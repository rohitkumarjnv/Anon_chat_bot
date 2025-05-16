import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

users = {}
waiting = {"male": [], "female": [], "other": []}
chats = {}

GENDER, CHATTING = range(2)
gender_keyboard = ReplyKeyboardMarkup([["male", "female", "other"]], one_time_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in chats:
        await update.message.reply_text("You are already in a chat. Use /stop to leave it.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome to Anonymous Chat!\nPlease select your gender:",
        reply_markup=gender_keyboard
    )
    return GENDER

async def set_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gender = update.message.text.lower()
    user_id = update.effective_user.id

    if gender not in waiting:
        await update.message.reply_text("Please choose a valid gender.")
        return GENDER

    users[user_id] = gender
    await update.message.reply_text("Looking for a partner...")

    for g in waiting:
        for uid in waiting[g]:
            if users[uid] != gender and uid != user_id:
                waiting[g].remove(uid)
                chats[user_id] = uid
                chats[uid] = user_id

                await context.bot.send_message(uid, "You are now connected! Say hi.\nUse /stop or /next anytime.")
                await update.message.reply_text("Connected! Say hi.\nUse /stop or /next anytime.")
                return ConversationHandler.END

    waiting[gender].append(user_id)
    return CHATTING

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user.id
    if sender in chats:
        receiver = chats[sender]
        try:
            await context.bot.send_message(receiver, update.message.text)
        except:
            await update.message.reply_text("Failed to send message.")
    else:
        await update.message.reply_text("You're not in a chat. Use /start to find a partner.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in chats:
        partner = chats.pop(user_id)
        chats.pop(partner, None)
        await context.bot.send_message(partner, "Your partner has left the chat.")
        await update.message.reply_text("You have left the chat.")
    elif user_id in waiting.get(users.get(user_id, ""), []):
        waiting[users[user_id]].remove(user_id)
        await update.message.reply_text("You have left the waiting queue.")
    else:
        await update.message.reply_text("You're not in a chat.")
    return ConversationHandler.END

async def next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop(update, context)
    return await start(update, context)

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /start to begin chatting.")

app = ApplicationBuilder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_gender)],
        CHATTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)],
    },
    fallbacks=[
        CommandHandler("stop", stop),
        CommandHandler("next", next),
        MessageHandler(filters.ALL, fallback)
    ]
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CommandHandler("next", next))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling()
