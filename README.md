>[!tip]
>**やっぱり** - "yappari", Japanese for "As i thought" / "Indeed"

# YAPPARI!

## Yet Another Prompt-based Personal Assistant Robot, Indeed!

It's a simple, easy-to-use GPT integration into Telegram.

Functionality:
- Basic GPT promptage
- YouTube video summary
- Image recognition (OpenAI Vision)
- Settings:
	- model
	- prompt
	- temperature
	- max_tokens
	- max_history_tokens
- Allowlisting buddies to share your bot with

## Installation & setup
### Option 1 - docker
```bash
git clone https://github.com/BoopyTheFox/YAPPARI
cd YAPPARI
./y_init_docker.sh BOT_OWNER, BOT_TOKEN, OPENAI_API_KEY
```
### Option 2 - systemd service
```bash
git clone https://github.com/BoopyTheFox/YAPPARI
cd YAPPARI
sudo ./y_init_systemd.sh BOT_OWNER, BOT_TOKEN, OPENAI_API_KEY
```
>To quickly remove: `sudo ./y_init_systemd.sh --uninstall`
### Option 3 - using it manually
```sh
git clone https://github.com/BoopyTheFox/YAPPARI
cd YAPPARI/app
python -m venv . && source bin/activate # activate.fish for fish, activate.csh for csh
pip install -r requirements.txt
$EDITOR y_secrets.env # put your secrets here manually
python y_bot.py
```
### Acquiring secrets:
#### BOT_OWNER
It is your **username** in telegram. Currently bot does not support operations without a username.
#### BOT_TOKEN
1. Go to `@BotFather` in Telegram
2. `/start` them (if didn't already)
3. `/newbot` - follow simple instructions on naming your bot
4. Copy your token
#### OPENAI_API_KEY
1. Go to https://platform.openai.com/api-keys
2. `+ Create new secret key`, name your key
3. Copy your key

## How to use
After installing and starting your bot:
Navigate to it in Telegram --> `/start` --> `/help`

## How to contribute
- Find `level=logging.WARNING` in `y_bot.py` and change it to `level=logging.DEBUG` to see more.
- Here are the **docs** if you need them:
	- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
	- [python-telegram-bot docs](https://docs.python-telegram-bot.org/)
	- [Telegram Bot API](https://core.telegram.org/bots/api)

## Known issues
- If you set it up with docker and it throws OpenAI errors - make sure docker's network is not routed through a network that 403's it
- Since it's a polling bot, sometimes `getUpdates` from telegram gets stuck a bit (especially on an unstable network) - just resend message one more time
