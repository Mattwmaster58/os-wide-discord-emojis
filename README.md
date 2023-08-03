## OS-Wide Discord Emojis
This repo contains the tools to download and use Discord emojis anywhere you can paste images with the help of the excellent [CopyQ](https://copyq.readthedocs.io/en/latest/).

# Warning

This script uses libraries that enable "self botting", which is explicitly against Discord's ToS. Accounts you use with this script may be banned. It is recommended to create an alternate account and join the servers you'd like to use.

## Demo
![TeamsDemo.gif](demo%2FTeamsDemo.gif)
## Features
 - Fast and near universal
 - Animated and static emoji support
 - Normalize emoji size

## Installation

### Prerequisites
 - [CopyQ](https://copyq.readthedocs.io/en/latest/) installed
 - Discord self-token. This is the value `Authorization` the authorization header which you can inspect in your browser or client.
 - Python with necessary libraries:
```bash
python -m venv venv
source ./venv/bin/activate # or ./venv/Scripts/activate on windows
pip install -r requirements.txt
```
 - `ffmpeg` accessible in your PATH variable if you want to normalize the size of Emojis (recommended. If you don't, emojis will paste in their native size, and will also be listed in their native size, depending on CopyQ settings)

### Step 1: Download and normalize emojis
Make sure the DISCORD_TOKEN environment variable is set, optionally through a .env file.
```bash
python cli.py download --normalize 128
```
Example output:
```bash
[2023-08-03 15:02:38] [INFO    ] discord.client: Logging in using static token.
[2023-08-03 15:02:39] [WARNING ] discord.utils: Info API down. Falling back to manual fetching...
[2023-08-03 15:02:40] [INFO    ] discord.http: Found user agent Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.
[2023-08-03 15:02:40] [INFO    ] discord.gateway: Connected to Gateway (Session ID: <id>).
Successfully auth-ed in as "<user>" with ID <id>
enumerated all 2027 emojis in 0.000s
100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 2027/2027 
downloaded all 2027 emojis in 0.203s. 2027 existing, 0 downloaded
normalizing emojis
100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 2027/2027 [00:00<00:00, 10268.77it/s] 
normalized all 2027 emojis in 0.474s. 2027 skipped, 0 processed

```
For a full list of available options, run `cli.py download --help`.

### Step 2: Generate a CopyQ command file

Example:
```bash
python cli.py generate
```
Example output:
```bash
generating plugin from template
saved command to C:/Users/<user>/universal-discord-emojis/universal-emoji.autogenerated.ini
```
For a full list of available options, run `cli.py generate --help`.

### Step 3: Import the command into CopyQ

 - Open CopyQ
 - Press F6 to open the command window
 - Click "Load Commands..."
 - Select the file generated in the previous step


