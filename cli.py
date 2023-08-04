import argparse
import os
from pathlib import Path


try:
    import dotenv
    from appdirs import user_data_dir

    from dumper import Dumper
    from plugin_generator import generate_plugin
except ImportError:
    print("did you install necessary requirements?")
    raise

DUMP_COMMAND = "dump"
GENERATE_COMMAND = "generate"


def main():
    dotenv.load_dotenv()
    parser = argparse.ArgumentParser(
        description="Universal Discord Emoji",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    subparser = parser.add_subparsers(dest="command")
    add_dump_parser(subparser)
    add_generate_parser(subparser)
    args = parser.parse_args()

    if args.command == DUMP_COMMAND:
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print(
                "DISCORD_TOKEN env variable not set. Create a .env file or set it in your terminal"
            )
            return

        dumper = Dumper(token, Path(args.emoji_dir))
        if not args.normalize_only:
            dumper.dump_emojis(force_refresh=args.refresh)
        if args.normalize is not None:
            dumper.normalize(args.normalize)

    elif args.command == GENERATE_COMMAND:
        print("generating plugin from template")
        emoji_dir = Path(args.emoji_dir)
        generate_plugin(
            command_name=args.command_name,
            command_shortcut=args.command_shortcut,
            emoji_dir=emoji_dir.absolute().as_posix(),
            emoji_load_limit=args.emoji_load_limit,
        )


def add_dump_parser(subparsers):
    parser_download = subparsers.add_parser(DUMP_COMMAND, help="Updates emojis based on the servers you are in")
    parser_download.add_argument(
        "--emoji-dir",
        type=str,
        help="Directory to store emojis in. Will be created if it does not exist",
        default=user_data_dir("universal-discord-emojis"),
    )
    parser_download.add_argument(
        "--refresh",
        type=bool,
        help="By default, emojis are not downloaded if already present. "
             "If this flag is specified, all emojis are downloaded whether they currently exist or not.",
        default=False
    )
    parser_download.add_argument(
        "--normalize",
        type=int,
        help="What size to normalize emojis to, 64-128 is recommended. "
             "This operation requires the ffmpeg variable to be in the path, as pure python solutions are quite slow. "
             "By default, this is not done",
        default=None,
    )
    parser_download.add_argument(
        "--normalize-only",
        type=bool,
        help="Don't download anything, only normalize ALL emojis already downloaded, "
              "including emojis which may have have already been normalized. "
              "If the input and output size are the same, no degrading in quality is expected. "
              "--normalize must also be specified for any normalization to take place.",
        default=False
    )


def add_generate_parser(subparsers):
    parser_generate = subparsers.add_parser(GENERATE_COMMAND, help="Generate something")
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
        default=50,
    )
    parser_generate.add_argument(
        "--command-name",
        type=str,
        help="Name of the command in CopyQ",
        default="Universal Emoji",
    )
    parser_generate.add_argument(
        "--command-shortcut",
        type=str,
        help="Shortcut to trigger command in CopyQ",
        default="ctrl+shift+;",
    )


if __name__ == "__main__":
    main()
