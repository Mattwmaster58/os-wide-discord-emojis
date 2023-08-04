import asyncio
import subprocess
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import discord
import os
import sys
import urllib.request

import dotenv
from tqdm import tqdm
from appdirs import user_data_dir
from slugify import slugify


class Downloader:
    def __init__(self, token: str, output_path: Path):
        self.token = token
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.client = discord.Client()
        self.enumerated_emojis: dict[str, list[discord.Emoji]] = {}
        self.dump_start_time = None

    def dump_emojis(self):
        self.dump_start_time = datetime.utcnow()
        # listen for on_ready even upon logging in
        self.client.event(self.on_ready)
        # runs until client close, this will populate self.enumerated_emojis
        self.client.run(self.token)
        # download all enumerate emojis (no auth needed)
        asyncio.run(self._dump_enumerated_emojis())

    def normalize(self, size: int):
        """Normalizes all emojis, static and animated to a specified size with ffmpeg"""
        start = time.perf_counter()
        print("normalizing emojis")
        size = int(size)
        total_processed = total_skipped = 0
        for child in tqdm([*self.output_path.iterdir()], miniters=1):
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
                    # if it's a gif, we need to explicitly generate a palette from the source gif, and then later
                    # use that palette to re-encode the output gif. My understanding is that without an explicit
                    # specification of a palette, a standard palette without transparency is used,
                    # effectively deleting any transparency effects from the gif
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
                        f"file does not exist or is 0 in size"
                    )
                else:
                    child.unlink()
                    temp_file.rename(child)
                    total_processed += 1
        print(
            f"normalized all {total_skipped + total_processed} emojis in {(time.perf_counter() - start):.3f}s. "
            f"{total_skipped} skipped, {total_processed} processed"
        )


    async def on_ready(self):
        """
        This function name is important, otherwise the client won't notify us of the "ready" event.
         We use this to proxy to our real on_ready function, which is named in line with what it actually does
        """
        print(
            f'Successfully auth-ed in as "{self.client.user.name}" with ID {self.client.user.id}'
        )
        await self._enumerate_emojis()

    async def _dump_enumerated_emojis(self) -> None:
        start = time.perf_counter()
        n_downloaded = 0
        all_emojis = sum(len(x) for x in self.enumerated_emojis.values())
        prog = tqdm(
            self.enumerated_emojis.items(),
            total=all_emojis,
            unit="emojis",
            unit_scale=True,
            unit_divisor=1000,
            miniters=1,
        )
        for guild, emojis in prog:
            for em in emojis:
                f_stem = f"{self.internal_slug(guild)}.{self.internal_slug(em.name)}"
                # all emojis are either GIF or PNG as of time of writing
                suffix = "gif" if em.animated else "png"
                f_path = self.output_path / f"{f_stem}.{suffix}"
                if not f_path.exists():
                    n_downloaded += 1
                    with open(f_path, "wb") as outFile:
                        # send a different header because otherwise we get a 403
                        req = urllib.request.Request(
                            em.url, headers={"User-Agent": "Mozilla/5.0"}
                        )
                        data = urllib.request.urlopen(req).read()
                        outFile.write(data)
                prog.update(1)
        print(
            f"downloaded all {all_emojis} emojis in {(time.perf_counter() - start):.3f}s. "
            f"{all_emojis - n_downloaded} existing, {n_downloaded} downloaded"
        )

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
            f"enumerated all {sum(len(x) for x in guild_to_emojis.values())} "
            f"emojis in {(time.perf_counter() - start):.3f}s"
        )

        # important: this must be last, this yields to the event loop (obviously)
        await self.client.close()

    @staticmethod
    def internal_slug(inp: str) -> str:
        """We use '.' for our own meaning somewhere else, thus replace this from the guild name"""
        return slugify(inp).replace(".", "_")
