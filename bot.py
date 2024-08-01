import os
import logging
import sqlite3
from telegram import (
    InlineKeyboardButton,
    KeyboardButtonPollType,
    Poll,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    PollAnswerHandler,
    PollHandler,
    filters,
)
from helpers import gen_pdf, update_to_json_file, cleanup
from keys import bot_token, bot_username

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Conect to database
conn = sqlite3.connect('zagzoga.db')
c = conn.cursor()


async def chatUpdateHandler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received update: {update.to_dict()}")
    mychat = update.my_chat_member
    if mychat.chat.type == "channel":
        channel_id = mychat.chat.id
        user = mychat.from_user
        if mychat.new_chat_member.status == "administrator":
            # The bot was added to a chat
            channel_username = mychat.chat.username
            add_channel(channel_id, channel_username)
            add_user(user.id, user.username)
            record_bot_addition(channel_id, user.id)
            await context.bot.sendMessage(chat_id=user.id,
                                          text=f"You added me to @{mychat.chat.username} channel")
        else:
            remove_from_db(channel_id, user.id)
            await context.bot.sendMessage(chat_id=user.id,
                                          text=f"You deleted me from @{mychat.chat.username} channel")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.sendMessage(chat_id=update.effective_chat.id, text="hi, it's zagzoga bot. give me your pdf for a singel topic")


async def helpHandler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.sendMessage(chat_id=update.effective_chat.id, text="using /start to convert a csv to pdf")


async def csvHandler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    csvfile = await context.bot.getFile(document.file_id)
    parts = document.file_name.split("-")
    module, subject, topic = parts
    topic = topic.split(".")[0]

    download_path = f"./data/{module}/{subject}"
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    await csvfile.download_to_drive(custom_path=f"{download_path}/{document.file_name}")

    await context.bot.sendMessage(chat_id=update.effective_chat.id, text= "your file is being processed.")
    global pdfpath
    pdfpath = gen_pdf(f"{download_path}/{document.file_name}", False)
    global anspath
    anspath = gen_pdf(f"{download_path}/{document.file_name}", True)

    # Check if the user is an admin in any channel
    user_id = update.effective_user.id
    query = "SELECT channel_id FROM bot_additions WHERE added_by_user_id = ?"
    execute_query(query, (user_id,))
    channels = c.fetchall()
    if not channels:
        await context.bot.sendDocument(chat_id=update.effective_chat.id, document=pdfpath)
        await context.bot.sendDocument(chat_id=update.effective_chat.id, document=anspath)
        to_remove = [pdfpath, anspath, download_path]
        cleanup(to_remove)
        return

    # Get channel info and post a message to it
    keyboard_rows = []
    for channel in channels:
        channel_info = await context.bot.get_chat(channel[0])
        channel_username = channel_info.username
        button = InlineKeyboardButton(text=channel_username, callback_data=f"channel_id:{channel[0]}")
        current_row = [button]
        keyboard_rows.append(current_row)

    reply_markup = InlineKeyboardMarkup(keyboard_rows)
    await update.message.reply_text("Please choose:", reply_markup=reply_markup)
    return


async def post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    update_to_json_file(update, "test.json")
    logger.info(f"Received call_back: {update.to_dict()}")
    query = update.callback_query
    channel_id = query.data.split(":")[1]
    channel_info = await context.bot.get_chat(channel_id)
    channel_username = channel_info.username
    await query.edit_message_text(text=f"Selected channel: @{channel_username}")
    global pdfpath
    global anspath
    await context.bot.sendDocument(chat_id=channel_id, document=pdfpath)
    await context.bot.sendDocument(chat_id=channel_id, document=anspath)
    await context.bot.sendMessage(chat_id=update.effective_chat.id, text=f"your file has been posted to @{channel_username}.")


async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received update: {update.to_dict()}")


def execute_query(query, params=()):
    global c
    c.execute(query, params)
    conn.commit()


def add_channel(channel_id, channel_username):
    query = "INSERT OR REPLACE INTO channels (channel_id, channel_username) VALUES (?, ?)"
    execute_query(query, (channel_id, channel_username))


def add_user(user_id, username):
    query = "INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)"
    execute_query(query, (user_id, username))


def record_bot_addition(channel_id, added_by_user_id):
    query = "INSERT OR REPLACE INTO bot_additions (channel_id, added_by_user_id) VALUES (?, ?)"
    execute_query(query, (channel_id, added_by_user_id))


def remove_from_db(channel_id, user_id):
    # Define the queries to delete data from the three tables
    queries = [
        "DELETE FROM channels WHERE channel_id = ?",
        "DELETE FROM users WHERE user_id = ?",
        "DELETE FROM bot_additions WHERE channel_id = ?"
    ]
    for query in queries:
        if "users" in query:
            execute_query(query, (user_id,))
        else:
            execute_query(query, (channel_id,))


def main():
    app = Application.builder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", helpHandler))

    app.add_handler(ChatMemberHandler(chatUpdateHandler))
    app.add_handler(CallbackQueryHandler(post))

    app.add_handler(MessageHandler(filters.Document.MimeType("text/csv") | filters.Document.MimeType("text/comma-separated-values"), csvHandler))
    app.add_handler(MessageHandler(filters.ALL, log_update))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
