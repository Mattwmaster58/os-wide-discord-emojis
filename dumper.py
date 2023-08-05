import asyncio
import subprocess
import time
from collections import defaultdict
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Tuple, Iterable

import discord
import os
import sys
import urllib.request

import dotenv
import httpx
from tqdm import tqdm
from appdirs import user_data_dir
from slugify import slugify


class Dumper:
    def __init__(self, token: str, output_path: Path):
        self.token = token
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.client = discord.Client()
        self.enumerated_emojis: dict[str, list[discord.Emoji]] = {}
        self.dump_start_time = None

    def dump_emojis(self, force_refresh: bool):
        self.dump_start_time = datetime.utcnow()
        # listen for on_ready even upon logging in
        self.client.event(self.on_ready)
        # runs until client close, this will populate self.enumerated_emojis
        self.client.run(self.token)
        # download all enumerate emojis (no auth needed)
        asyncio.run(self._dump_enumerated_emojis(force_refresh))

    def normalize(self, size: int):
        """Normalizes all emojis, static and animated to a specified size with ffmpeg"""
        start = time.perf_counter()
        print(f"Normalizing emojis to size: {size}x{size}")
        size = int(size)
        total_processed = total_skipped = 0
        for child in tqdm([*self.output_path.iterdir()], miniters=1, unit="emojis"):
            if child.is_file() and child.suffix in (".png", ".gif"):
                # is mtime on linux, works for us
                child_creation_time = datetime.utcfromtimestamp(child.stat().st_ctime)
                if self.dump_start_time and child_creation_time < self.dump_start_time:
                    # child wasn't created by this run of the script, don't process it
                    total_skipped += 1
                    continue
                temp_file = child.with_stem(f"{child.stem}_temp")
                complex_filters = [f"[0:v]scale=-1:{size}:flags=lanczos"]
                if child.suffix == ".gif":
                    # if it's a GIF, we need to explicitly generate a palette from the source gif, and then
                    # use that same palette to re-encode the output GIF. My understanding is that without an explicit
                    # specification of a palette, a standard palette without transparency is used,
                    # effectively deleting any transparency effects from the GIF
                    # see: https://ffmpeg.org/ffmpeg-filters.html#Filtergraph-description
                    complex_filters.append("split [a][b];[a]palettegen [p];[b][p]paletteuse")
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        *["-i", child.absolute().as_posix()],
                        *["-filter_complex", ",".join(complex_filters)],
                        temp_file.absolute().as_posix(),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if not temp_file.exists() or temp_file.stat().st_size == 0:
                    raise ValueError(
                        f"failed to convert {temp_file.absolute().as_posix()}. "
                        f"file does not exist or is 0 in size. Aborting operation"
                    )
                else:
                    child.unlink()
                    temp_file.rename(child)
                    total_processed += 1
        print(
            f"Normalized {total_skipped + total_processed} emojis in {(time.perf_counter() - start):.3f}s "
            f"({total_skipped} skipped, {total_processed} processed)"
        )

    async def on_ready(self) -> None:
        """
        This function name is important, otherwise the client won't notify us of the "ready" event.
         We use this to proxy to our real on_ready function, which is named in line with what it actually does
        """
        print(
            f'Successfully auth-ed in as "{self.client.user.name}" with ID {self.client.user.id}'
        )
        await self._enumerate_emojis()

    async def _dump_enumerated_emojis(self, force_refresh: bool) -> None:
        start = time.perf_counter()
        total_bytes_downloaded = total_downloaded = 0
        all_emojis = sum(len(x) for x in self.enumerated_emojis.values())
        progress_bar = tqdm(
            total=all_emojis,
            unit="emojis",
            unit_scale=True,
            unit_divisor=1000,
            mininterval=0.25,
        )

        CONCURRENT_DOWNLOADS_LIMIT = 8
        client = httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(retries=2))
        async_tasks = set()

        for guild, emojis in self.enumerated_emojis.items():
            for em in emojis:
                if len(async_tasks) >= CONCURRENT_DOWNLOADS_LIMIT:
                    # wait until at least one task completes before adding a new one
                    finished_tasks, async_tasks = await asyncio.wait(async_tasks, return_when=asyncio.FIRST_COMPLETED)
                    emojis_downloaded, bytes_downloaded = self._unwrap_download_emoji_job_info(finished_tasks)
                    total_downloaded += emojis_downloaded
                    total_bytes_downloaded += bytes_downloaded
                    progress_bar.update(len(finished_tasks))
                async_tasks.add(asyncio.create_task(self._download_emoji_job(client, em, force_refresh)))
        # Wait for the remaining downloads to finish,
        # (there will be no pending tasks, _ are pending)
        rest_of_tasks, _ = await asyncio.wait(async_tasks)
        emojis_downloaded, bytes_downloaded = self._unwrap_download_emoji_job_info(rest_of_tasks)
        total_downloaded += emojis_downloaded
        total_bytes_downloaded += bytes_downloaded
        progress_bar.update(len(rest_of_tasks))

        def format_unit(num: float) -> str:
            return tqdm.format_sizeof(num, suffix="b")

        time_taken = time.perf_counter() - start
        print(
            f"Updated {all_emojis} emojis from {len(self.enumerated_emojis)} servers in {time_taken:.3f}s. "
            f"{format_unit(total_bytes_downloaded)} downloaded ({format_unit(total_bytes_downloaded / time_taken)}/s). "
            f"{total_downloaded} downloaded from possible {all_emojis} ({all_emojis - total_downloaded} skipped)"
        )

    async def _download_emoji_job(self, client: httpx.AsyncClient, emoji: discord.Emoji, force_refresh: bool) -> int:
        # all emojis are either GIF or PNG as of time of writing
        suffix = "gif" if emoji.animated else "png"
        f_stem = f"{self.internal_slug(emoji.guild.name)}.{self.internal_slug(emoji.name)}"
        f_path = self.output_path / f"{f_stem}.{suffix}"

        if not force_refresh and f_path.exists():
            return 0

        try:
            # can we even open the file?
            # don't download the emoji if we can't
            open(f_path, "a").close()
            f_path.unlink()
        except Exception:
            return 0

        # send a different header because otherwise we get a 403
        req = await client.get(emoji.url, headers={"User-Agent": "Mozilla/5.0"})
        if req.status_code != 200:
            return 0

        with open(f_path, "wb") as emoji_file:
            emoji_file.write(req.content)
            return len(req.content)

    async def _enumerate_emojis(self):
        start = time.perf_counter()
        guild_to_emojis = defaultdict(list)
        for guild in self.client.guilds:
            for emoji in guild.emojis:
                guild_to_emojis[guild.name].append(emoji)
        # freeze the default dict
        guild_to_emojis.default_factory = None
        self.enumerated_emojis = guild_to_emojis
        print(
            f"Enumerated {sum(len(x) for x in guild_to_emojis.values())} "
            f"emojis in {(time.perf_counter() - start):.3f}s"
        )

        # important: this must be last, this yields to the event loop (obviously)
        await self.client.close()

    @staticmethod
    def _unwrap_download_emoji_job_info(tasks: Iterable[asyncio.Future]) -> Tuple[int, int]:
        """Given a list of tasks, returns the number successful and bytes downloaded"""
        total_bytes_downloaded = 0
        total_emojis_downloaded = 0
        for t in tasks:
            if t.done():
                try:
                    bytes_downloaded = t.result()
                    total_bytes_downloaded += bytes_downloaded
                    total_emojis_downloaded += bool(bytes_downloaded)
                except:
                    raise ValueError("This should have never happened: "
                                     "the task should have handled all exceptions itself, please open an issue")
            else:
                raise ValueError("you should only be passing finished tasks here, "
                                 "it seems the developer messed up, please open an issue")
        return total_emojis_downloaded, total_bytes_downloaded

    @staticmethod
    def internal_slug(inp: str) -> str:
        """We use '.' for our own meaning somewhere else, thus replace this from the guild name"""
        return slugify(inp).replace(".", "_")
