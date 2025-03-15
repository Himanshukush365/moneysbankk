from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import motor.motor_asyncio  # Async MongoDB
import asyncio
import re

# 🤮 Async MongoDB Setup
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://Himanshu06:Himanshu@2007@cluster0.t8z2y.mongodb.net/billing_bot?retryWrites=true&w=majority")
db = client["billing_bot"]
users_collection = db["users"]

# 👑 Admin ID (Replace with your Telegram ID)
ADMIN_ID = 6233383218  

# 🔑 Bot Token (Replace with your Telegram Bot Token)
BOT_TOKEN = "8105667535:AAEdXsYFQXdeSnKVoR2P6jEgltCpE_kiq0k"

# 🔹 States
UPDATE_BALANCE, BROADCAST_MESSAGE, SET_NICKNAME = range(3)

# 🏠 Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    await users_collection.update_one({"user_id": user_id}, {"$setOnInsert": {"balance": 0, "nickname": f"User_{user_id}"}}, upsert=True)
    await update.message.reply_text("✅ Welcome to the Billing Bot!")
    await show_panel(update, context)

# 🌟 Customer Panel
async def customer_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["💰 CHECK BALANCE"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🔹 SELECT AN OPTION:", reply_markup=reply_markup)

# 👑 Admin Panel
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["✏️ UPDATE BALANCE"],
        ["📢 BROADCAST MESSAGE"],
        ["📋 VIEW BALANCES"],
        ["🔤 SET NICKNAME"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🔹 ADMIN PANEL:", reply_markup=reply_markup)

# 🌟 Role-Based Panel
async def show_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id == ADMIN_ID:
        await admin_panel(update, context)
    else:
        await customer_panel(update, context)

# 💰 Check Balance
async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user = await users_collection.find_one({"user_id": user_id})
    balance = user["balance"] if user else 0
    await update.message.reply_text(f"💰 Your current balance: ₹{balance}")

# 👛 View Balances
async def view_balances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await users_collection.find().to_list(length=100)
    if not users:
        await update.message.reply_text("📋 No users found!")
        return
    
    message = "📋 User Balances:\n"
    for user in users:
        message += f"👤 {user.get('nickname', 'Unknown')} ({user['user_id']}): ₹{user['balance']}\n"
    
    await update.message.reply_text(message)

# ✏️ Update Balance
async def update_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✏️ Send user ID and new balance in format: user_id amount")
    return UPDATE_BALANCE

async def update_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID:
        return ConversationHandler.END
    try:
        user_id, amount = map(int, update.message.text.split())
        await users_collection.update_one({"user_id": user_id}, {"$set": {"balance": amount}}, upsert=True)
        await update.message.reply_text(f"✅ Updated balance for user {user_id} to ₹{amount}")
    except:
        await update.message.reply_text("❌ Invalid format. Use: user_id amount")
    return ConversationHandler.END

# 🔤 Set Nickname
async def set_nickname_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔤 Send user ID and new nickname in format: user_id nickname")
    return SET_NICKNAME

async def set_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID:
        return ConversationHandler.END
    try:
        parts = update.message.text.split(maxsplit=1)
        user_id = int(parts[0])
        nickname = parts[1]
        await users_collection.update_one({"user_id": user_id}, {"$set": {"nickname": nickname}}, upsert=True)
        await update.message.reply_text(f"✅ Updated nickname for user {user_id} to {nickname}")
    except:
        await update.message.reply_text("❌ Invalid format. Use: user_id nickname")
    return ConversationHandler.END

# 📢 Broadcast Message
async def broadcast_message_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📢 Send the message you want to broadcast:")
    return BROADCAST_MESSAGE

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID:
        return ConversationHandler.END
    message = update.message.text
    users = await users_collection.find().to_list(length=1000)
    for user in users:
        try:
            await context.bot.send_message(chat_id=user['user_id'], text=f"📢 Broadcast: {message}")
        except:
            pass
    await update.message.reply_text("✅ Message broadcasted to all users.")
    return ConversationHandler.END

# 🔥 Handling Button Clicks
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💰 CHECK BALANCE":
        await check_balance(update, context)
    elif text == "✏️ UPDATE BALANCE":
        return await update_balance_prompt(update, context)
    elif text == "📢 BROADCAST MESSAGE":
        return await broadcast_message_prompt(update, context)
    elif text == "📋 VIEW BALANCES":
        await view_balances(update, context)
    elif text == "🔤 SET NICKNAME":
        return await set_nickname_prompt(update, context)

# 🔥 Bot Initialization
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler)],
        states={
            UPDATE_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_balance)],
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message)],
            SET_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_nickname)]
        },
        fallbacks=[]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()

