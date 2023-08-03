import argparse
import os
from pathlib import Path

from generate_plugin import generate_plugin

try:
    import dotenv
    from appdirs import user_data_dir

    from update_emojis import Downloader
except ImportError:
    print("did you install necessary requirements?")
    raise


def main():
    dotenv.load_dotenv()
    parser = argparse.ArgumentParser(
        description="A tool with subcommands: download and generate"
    )

    subparsers = parser.add_subparsers(dest="command")
    parser_download = subparsers.add_parser("download", help="Download a file")
    parser_download.add_argument(
        "--emoji-dir",
        type=str,
        help="Directory to store emojis in. Will be created if it does not exist",
        default=user_data_dir("universal-discord-emojis"),
    )

    parser_download.add_argument(
        "--normalize",
        type=int,
        nargs="?",
        help="Whether to normalize emoji size and if so, what size. "
        "Not specifying any size will use the default. "
        "By default, this is not done",
        default=None,
    )
    parser_download.add_argument("url", help="URL to the file to download")

    parser_generate = subparsers.add_parser("generate", help="Generate something")
    parser_generate.add_argument(
        "--emoji-dir",
        type=str,
        help="Directory to search for emojis in",
        default=user_data_dir("universal-discord-emojis"),
    )
    parser_generate.add_argument(
        "--emoji-load-limit",
        type=int,
        help="Number of emojis to load to the clipboard",
        default=25,
    )
    args = parser.parse_args()
    if args.command == "download":
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print(
                "DISCORD_TOKEN env variable not set. Create a .env file or set it elsewhere"
            )
            return

        downloader = Downloader(token, Path(args.emoji_dir))
        downloader.dump_emojis()
    elif args.command == "generate":
        print("generating plugin from template")
        generate_plugin(
            emoji_dir=args.emoji_dir,
            emoji_load_limit=args.emoji_load_limit,
        )


if __name__ == "__main__":
    main()
