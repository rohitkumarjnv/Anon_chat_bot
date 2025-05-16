from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatAction
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
import time
from flask import Flask
from threading import Thread

users = {}
waiting_users = []
pairs = {}
last_message_time = {}

# Anti-spam delay in seconds
SPAM_DELAY = 3

# Keep-alive for Replit
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Bot is Alive!"

def run():
    flask_app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Male", callback_data='gender_Male')],
        [InlineKeyboardButton("Female", callback_data='gender_Female')],
        [InlineKeyboardButton("Other", callback_data='gender_Other')]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose your gender:", reply_markup=markup)

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("gender_"):
        gender = data.split("_")[1]
        users[user_id] = {'gender': gender, 'preferred': '', 'chatting_with': None}
        keyboard = [
            [InlineKeyboardButton("Male", callback_data='pref_Male')],
            [InlineKeyboardButton("Female", callback_data='pref_Female')],
            [InlineKeyboardButton("Other", callback_data='pref_Other')],
            [InlineKeyboardButton("Any", callback_data='pref_Any')]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Who do you want to chat with?", reply_markup=markup)

    elif data.startswith("pref_"):
        users[user_id]['preferred'] = data.split("_")[1]
        await query.message.reply_text("Finding a partner...")
        await find_match(user_id, context)

# Matchmaking
async def find_match(user_id, context):
    user = users[user_id]
    for other_id in waiting_users:
        other = users.get(other_id)
        if other and other['chatting_with'] is None:
            if (user['preferred'] == 'Any' or other['gender'] == user['preferred']) and \
               (other['preferred'] == 'Any' or user['gender'] == other['preferred']):
                # Match!
                users[user_id]['chatting_with'] = other_id
                users[other_id]['chatting_with'] = user_id
                pairs[user_id] = other_id
                pairs[other_id] = user_id
                waiting_users.remove(other_id)
                await context.bot.send_message(chat_id=user_id, text="You're now chatting. Say hi!")
                await context.bot.send_message(chat_id=other_id, text="You're now chatting. Say hi!")
                return
    # No match found
    if user_id not in waiting_users:
        waiting_users.append(user_id)

# Relay messages with spam control & typing
async def relay_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.message.from_user.id
    if sender_id not in users or not users[sender_id]['chatting_with']:
        await update.message.reply_text("You're not in a chat. Use /next to find a partner.")
        return

    now = time.time()
    if sender_id in last_message_time and now - last_message_time[sender_id] < SPAM_DELAY:
        return  # Too fast, ignore
    last_message_time[sender_id] = now

    receiver_id = users[sender_id]['chatting_with']
    try:
        await context.bot.send_chat_action(chat_id=receiver_id, action=ChatAction.TYPING)
        time.sleep(1.5)
        await context.bot.send_message(chat_id=receiver_id, text=update.message.text)
    except Exception:
        await update.message.reply_text("Message couldn't be delivered.")

# /stop command
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    partner_id = pairs.pop(user_id, None)
    if partner_id:
        pairs.pop(partner_id, None)
        users[user_id]['chatting_with'] = None
        users[partner_id]['chatting_with'] = None
        await context.bot.send_message(chat_id=partner_id, text="Your partner left the chat.")
    await update.message.reply_text("You left the chat.")

# /next command
async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop(update, context)
    await find_match(update.message.from_user.id, context)

# Initialize bot
keep_alive()
app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CommandHandler("next", next_chat))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_message))

print("Bot is running...")
app.run_polling()
