#!/usr/bin/env python

#############
## IMPORTS ##
#############

# General
import os
import sys
import logging
import base64
import re
from io import BytesIO

# Telegram
from telegram import (
    Update
)
from telegram.constants import (
    ChatAction,
    ParseMode
)
from telegram.ext import ( 
    Application, 
    CommandHandler, 
    MessageHandler,
    ContextTypes, 
    filters
)
from telegram.error import (
    BadRequest
)

# DB
from y_DB import (
    init_db, init_user,
    key_get, key_set, key_remove,
    chat_save, chat_load, chat_forget, chat_list,
)

# GPT
import openai
from y_GPT import (
    GPT_query,
    GPT_summarize,
    GPT_recognize
)


#############
## SECRETS ##
#############


from dotenv import load_dotenv
load_dotenv("y_secrets.env")
BOT_OWNER = os.getenv("BOT_OWNER")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print(BOT_TOKEN)

if not all([BOT_OWNER, BOT_TOKEN, OPENAI_API_KEY]):
    print("Please populate y_secrets.env with BOT_OWNER, BOT_TOKEN, OPENAI_API_KEY") 
    sys.exit(1)


######################
## HELPER_FUNCTIONS ##
######################


def load_allowed_users(filepath='y_allowed_users.txt'):
    allowed_users = []
    allowed_users.append(BOT_OWNER.lower())
    with open(filepath, 'r') as file:
        allowed_users = {line.strip().lower() for line in file if line.strip()}
    return allowed_users

def touch_file(filepath):
    if not os.path.exists(filepath):
        with open(filepath, 'w'):
            pass


#############
## LOGGING ##
#############

# Logging levels available are DEBUG, INFO, WARNING, ERROR, CRITICAL 
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)
logger = logging.getLogger(__name__)


###################
## BOT_FUNCTIONS ##
###################


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    username = update.message.from_user.username.lower()
    allowed_users = load_allowed_users()

    if username == BOT_OWNER.lower() or username in allowed_users:
        init_user(chat_id)
        username = update.message.from_user.username.strip()
        await update.message.reply_text(
            f'👋 Hey @{username}! I am YAPPARI!👋\n\n\
Yet Another Prompt-based Personal Assistant Robot, Indeed!\n\n\
I am just a wrapper for GPT, so i\'ll treat your messages as user prompts.\n\n\
❔If you wanna learn more, type /help anytime!❔'
        )
    else: 
        pass

## HELP ##

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username.lower()
    allowed_users = load_allowed_users()

    if username == BOT_OWNER.lower() or username in allowed_users:
        username = update.message.from_user.username.strip()
        if not username: 
            username = "user"

        response_msg = f'''
Hello, @{username}!
🤓 Just type anything, it will be passed to GPT.

📺 YouTube videos summary:
<video_link> <additional_questions>
youtu.be/dQw4w9WgXcQ What will he never do?

👀 Image recognition:
just send me a photo. 
You can also put your questions in caption.

📜 Save/Load chats:
/chats_forget | /f - forget current chat
    all - forget every chat
    <name> - to forget specific chat
/chats_save <name> | /save <name> - save current chat
/chats_load <name> | /load <name> - load some chat
/chats_list | /ls - list all saved chats

⚙️ Settings:
/settings | /s - list all settings
/setting <setting> <value> | /s <s> <v> - set a setting
Available settings:
prompt, model, temperature, max_tokens, max_history_tokens

😌 やっぱり!
        '''
        await update.message.reply_text(response_msg, disable_web_page_preview=True)
        if username.lower() == BOT_OWNER.lower():
            response_msg = '''
👑 Since you're bot owner, you also can also allow your friends to use your bot!
/users_allow <username> | /ua <username> - add a user to an allow list
/users_disallow <username> | /ud <username>- remove user from an allow list
/users_list | /u - show allowed_users.txt
            '''
            await update.message.reply_text(response_msg)

## HISTORY_MANAGEMENT ##

async def chats_forget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    chat_name = ' '.join(context.args)
    response_msg = chat_forget(chat_id=chat_id, chat_name=chat_name)
    await update.message.reply_text(response_msg)


async def chats_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    chat_name = ' '.join(context.args)
    if chat_name:
        chat_save(chat_id, chat_name)
        await update.message.reply_text(f"💾🔻 Chat history saved under the name '{chat_name}'.")
    else:
        await update.message.reply_text("❔ Please provide a name for the chat history.")


async def chats_load(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    chat_name = ' '.join(context.args)
    if not chat_name:
        await update.message.reply_text("❔ Please provide the name of the saved chat history to load.")
    else:
        response_msg = chat_load(chat_id=chat_id, chat_name=chat_name)
        await update.message.reply_text(response_msg)


async def chats_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    saved_chats = chat_list(chat_id)
    if saved_chats:
        chats_list_str = '\n'.join(saved_chats)
        await update.message.reply_text(f"📜 Saved chats:\n{chats_list_str}")
    else:
        await update.message.reply_text("🤷 No saved chats found.")

## USERS_MANAGEMENT ##
##   (owner only)   ##

async def users_allow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.username.lower() == BOT_OWNER.lower():
        username = ' '.join(context.args).strip().lower()
        if username and username != BOT_OWNER.lower():
            filepath = 'y_allowed_users.txt'
            touch_file(filepath)  # Ensure the file exists
            allowed_users = load_allowed_users(filepath)
            if username not in allowed_users:
                with open(filepath, 'a') as file:
                    file.write(username + '\n')
                await update.message.reply_text(f"✅ User '{username}' added to allowed users.")
            else:
                await update.message.reply_text(f"❌ User '{username}' is already in the allowed users list.")
        else:
            await update.message.reply_text("❓️ Invalid username")


async def users_disallow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.username.lower() == BOT_OWNER.lower():
        username = ' '.join(context.args).strip().lower()
        if username and username != BOT_OWNER.lower():
            filepath = 'y_allowed_users.txt'
            touch_file(filepath)  # Ensure the file exists
            allowed_users = load_allowed_users(filepath)
            if username in allowed_users:
                allowed_users.remove(username)
                with open(filepath, 'w') as file:
                    file.write('\n'.join(allowed_users) + '\n')
                await update.message.reply_text(f"✅ User '{username}' removed from allowed users.")
            else:
                await update.message.reply_text(f"❌ User '{username}' is not in the allowed users list.")
        else:
            await update.message.reply_text("❓️ Invalid username.")


async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.username.lower() == BOT_OWNER.lower():
        allowed_users = load_allowed_users()
        allowed_users_list = '\n'.join(allowed_users)
        await update.message.reply_text(f"👀 Allowed users:\n{allowed_users_list}")

## GPT_STUFF ##

MAX_MESSAGE_LENGTH = 4096 # Telegram requires to split large output


async def gpt_logic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    youtube_pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    message_text = update.message.text.strip()
    if not re.search(youtube_pattern, message_text.split()[0]):
        await gpt_query(update, context)
    else:
        await gpt_summarize(update, context)


async def gpt_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    username = update.message.from_user.username.lower()
    allowed_users = load_allowed_users()

    if username == BOT_OWNER.lower() or username in allowed_users: 
        await update.message.reply_text("Thinking... ⏳️")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        try:
            response_msg = await GPT_query(chat_id, update.message.text)
            for i in range(0, len(response_msg), MAX_MESSAGE_LENGTH):
                try:
                    await update.message.reply_text(response_msg[i:i + MAX_MESSAGE_LENGTH], parse_mode=ParseMode.MARKDOWN)
                except BadRequest:
                    await update.message.reply_text("⚠️ GPT generated a message with improperly closed markdown. Telegram doesn't like that.\n\nMarkdown is disabled for next message.")
                    await update.message.reply_text(response_msg[i:i + MAX_MESSAGE_LENGTH], parse_mode=ParseMode.HTML)
        except (openai.APIError, openai.RateLimitError):
            await update.message.reply_text("❌ OpenAI error. Try again? (also, better clear history)")


async def gpt_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    username = update.message.from_user.username.lower()
    allowed_users = load_allowed_users()

    if username == BOT_OWNER.lower() or username in allowed_users:
        await update.message.reply_text("Analyzing video transcript... ⏳️")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        message = update.message.text.strip().split(maxsplit=1)
        video_link = message[0]
        if len(message) > 1: 
            questions = message[1]
        else:
            questions = ""

        try:
            response_msg = await GPT_summarize(chat_id, video_link, questions)
            for i in range(0, len(response_msg), MAX_MESSAGE_LENGTH):
                await update.message.reply_text(response_msg[i:i + MAX_MESSAGE_LENGTH], parse_mode=ParseMode.MARKDOWN)
        except (openai.APIError, openai.RateLimitError):
            await update.message.reply_text("❌ OpenAI error. Try again? (also, better clear history)")


async def gpt_recognize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    username = update.message.from_user.username.lower()
    allowed_users = load_allowed_users()

    if username == BOT_OWNER.lower() or username in allowed_users:
        await update.message.reply_text("Analyzing image... ⏳️")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        # Download image directly into memory
        photo_id = update.message.photo[-1]
        bio = BytesIO()
        file = await photo_id.get_file()
        await file.download_to_memory(out=bio)
        bio.seek(0)
        
        # Convert to base64 to pass to OpenAI Vision
        base64_image = base64.b64encode(bio.read()).decode('utf-8')
        
        if update.message.caption:
            caption = update.message.caption
        else:
            caption = "What's in this image?"
        
        response = await GPT_recognize(chat_id, base64_image, caption)
        response_msg = response.message.content
        for i in range(0, len(response_msg), MAX_MESSAGE_LENGTH):
            await update.message.reply_text(response_msg[i:i + MAX_MESSAGE_LENGTH], parse_mode=ParseMode.MARKDOWN)

## SETTINGS ##

async def settings_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    username = update.message.from_user.username.lower()
    allowed_users = load_allowed_users()

    if username == BOT_OWNER.lower() or username in allowed_users:
        message = update.message.text.strip().split(maxsplit=2)
        if len(message) != 3:
            await update.message.reply_text("❓ Usage: /setting <setting> <value>")
            return

        key, value = message[1], message[2]
        if key in ['model', 'prompt', 'temperature', 'max_tokens', 'max_history_tokens']:
            if value == "default":
                key_remove(chat_id, key)
                await update.message.reply_text(f"✅ Setting '{key}' is back to default.")
            else:
                key_set(chat_id, key, value)
                await update.message.reply_text(f"✅ Setting '{key}' updated to '{value}'.")
        else:
            await update.message.reply_text("❌ Invalid key.\n\nValid keys are: model, prompt, temperature, max_tokens, max_history_tokens.")


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    username = update.message.from_user.username.lower()
    allowed_users = load_allowed_users()

    if username == BOT_OWNER.lower() or username in allowed_users:
        settings_keys = ['model', 'prompt', 'temperature', 'max_tokens', 'max_history_tokens']
        settings = {key: key_get(chat_id, key) or "default" for key in settings_keys}
        
        settings_message = "\n".join([f"{key}: {value}" for key, value in settings.items()])
        await update.message.reply_text(f"⚙️ Current settings:\n{settings_message}")


##########
## MAIN ##
##########


def main() -> None:

    init_db()
    touch_file('y_allowed_users.txt')

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler(["help", "h"],  help))

    application.add_handler(CommandHandler(["chats_forget", "f"], chats_forget))
    application.add_handler(CommandHandler(["chats_save", "save"], chats_save))
    application.add_handler(CommandHandler(["chats_load", "load"], chats_load))
    application.add_handler(CommandHandler(["chats_list", "ls"], chats_list))

    application.add_handler(CommandHandler(["users_allow", "ua"], users_allow))
    application.add_handler(CommandHandler(["users_disallow", "ud"], users_disallow))
    application.add_handler(CommandHandler(["users_list", "u"], users_list))

    application.add_handler(CommandHandler(["setting", "s"], settings_update))
    application.add_handler(CommandHandler(["settings", "ss"], settings))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_logic, block=False))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, gpt_recognize, block=False))

    application.run_polling()


if __name__ == "__main__":
    main()
