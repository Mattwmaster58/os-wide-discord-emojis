import os
from pathlib import Path

import dotenv
from appdirs import user_data_dir

from update_emojis.update_emojis import Downloader


def main():
    dotenv.load_dotenv()
    Downloader(
        os.getenv("DISCORD_TOKEN"), Path(user_data_dir("universal-discord-emojis"))
    ).dump_emojis()


if __name__ == "__main__":
    main()
