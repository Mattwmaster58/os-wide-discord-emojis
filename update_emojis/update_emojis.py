import asyncio
import time
from collections import defaultdict
from pathlib import Path

import discord
import os
import sys
import urllib.request

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

    def dump_emojis(self):
        # listen for on_ready even upon logging in
        self.client.event(self.on_ready)
        # runs until client close, this will populate self.enumerated_emojis
        self.client.run(self.token)
        # download all enumerate emojis (no auth needed)
        asyncio.run(self.dump_enumerated_emojis())

    async def dump_enumerated_emojis(self) -> None:
        all_emojis = sum(len(x) for x in self.enumerated_emojis.values())
        prog = tqdm(self.enumerated_emojis.items(), total=all_emojis, unit='emojis', unit_scale=True, unit_divisor=1000)
        for guild, emojis in prog:
            for em in emojis:
                f_stem = f'{self.internal_slug(guild)}.{self.internal_slug(em.name)}'
                # all emojis are either GIF or PNG as of time of writing
                suffix = "gif" if em.animated else "png"
                f_path = self.output_path / f"{f_stem}.{suffix}"
                if not f_path.exists():
                    with open(f_path, "wb") as outFile:
                        # send a different header because otherwise we get a 403
                        req = urllib.request.Request(
                            em.url, headers={"User-Agent": "Mozilla/5.0"}
                        )
                        data = urllib.request.urlopen(req).read()
                        outFile.write(data)
                prog.update(1)



    async def on_ready(self):
        """
        This function name is important, otherwise the client won't notify us of the "ready" event.
         We use this to proxy to our real on_ready function, which is named in line with what it actually does
         """
        print(f'Successfully auth-ed in as "{self.client.user.name}" with ID {self.client.user.id}')
        await self._enumerate_emojis()

    async def _enumerate_emojis(self):
        start = time.perf_counter()
        guild_to_emojis = defaultdict(list)
        for guild in self.client.guilds:
            for emoji in guild.emojis:
                guild_to_emojis[guild.name].append(emoji)
        # freeze the default dict
        guild_to_emojis.default_factory = None
        self.enumerated_emojis = guild_to_emojis
        print(f"enumerated all {sum(len(x) for x in guild_to_emojis.values())} emojis in {(time.perf_counter() - start):.3f}s")

        # important: this must be last, this yields to the event loop (obviously)
        await self.client.close()


    @staticmethod
    def internal_slug(inp: str) ->  str:
        """We use '.' for our own meaning somewhere else, thus replace this from the guild name"""
        return slugify(inp).replace(".", "_")


Downloader(
    "NDIwNzQ0NjExMjM4MTE3Mzc2.GGF8fZ.rLrfDicWjMeWbVN5bI44nylaHgFPzijQvlATjo",
    user_data_dir("universal-discord-emojis")
).dump_emojis()
