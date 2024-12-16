import random
import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define states
class WithdrawalStates(StatesGroup):
    waiting_for_phone_number = State()
    waiting_for_1xbet_id = State()  # New state for 1xbet ID

# Replace with your actual bot token
API_TOKEN = "7610826102:AAFe8Oy5aqF5AdxdDI1O9VG1oX5K-4Oz76w"

# Webhook settings
WEBHOOK_HOST = "https://dylan-sbot-2.onrender.com"  # Replace with your Render app URL
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Web server settings
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 5000

# Initialize Bot and Router
bot = Bot(token=API_TOKEN)
router = Router()

# Replace 'CHANNEL_ID' with your actual channel ID (must be an integer starting with -100)
CHANNEL_ID = -1001954879371  # Replace with your channel's ID
SECOND_CHANNEL_ID = -1002484382800  # Replace with the second channel's ID
SECOND_CHANNEL_LINK = "https://t.me/+oUsEqNov1vFkYzhk"

# Create and initialize the SQLite database
def init_db():
    conn = sqlite3.connect("utilisateurs.db")  # Database named "utilisateurs.db"
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY,
            nom TEXT,
            sold REAL DEFAULT 0.0,  -- "sold" for balance
            invite INTEGER DEFAULT 0  -- "invite" for number of invitations
        )
    """)
    conn.commit()
    conn.close()

# Add user to the database if not already there
def add_user_to_db(user_id, user_name):
    conn = sqlite3.connect("utilisateurs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM utilisateurs WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO utilisateurs (id, nom) VALUES (?, ?)", (user_id, user_name))
        conn.commit()
    conn.close()

# Start command handler
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Function to generate the main menu keyboard
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [  # First row: Solde and Retirer
                KeyboardButton(text="💰 Solde"),
                KeyboardButton(text="🏦 Retirer"),
            ],
            [  # Second row: Inviter, Bonus, Paramètre
                KeyboardButton(text="📨 Inviter"),
                KeyboardButton(text="🎁 Bonus"),
                KeyboardButton(text="⚙️ Paramètre"),
            ],
            [  # Third row: Comment ça marche
                KeyboardButton(text="❓ Comment ça marche"),
            ],
        ],
        resize_keyboard=True,  # Automatically adjust button size
        one_time_keyboard=False  # Keep the keyboard visible
    )

# Update to the send_welcome function
from aiogram.filters.command import CommandStart

@router.message(CommandStart())
async def send_welcome(message: types.Message, command: CommandStart, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    inviter_id = command.args

    try:
        # Check if the user is a member of the first channel
        member_first_channel = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member_first_channel.status in ["member", "creator", "administrator"]:
            # Check if the user is a member of the second channel
            member_second_channel = await bot.get_chat_member(chat_id=SECOND_CHANNEL_ID, user_id=user_id)
            if member_second_channel.status in ["member", "creator", "administrator"]:
                # Add the user to the database if not already there
                conn = sqlite3.connect("utilisateurs.db")
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM utilisateurs WHERE id = ?", (user_id,))
                user = cursor.fetchone()
                if not user:
                    add_user_to_db(user_id, user_name)
                conn.close()

                # If inviter_id is provided and is a valid user_id
                if inviter_id and inviter_id.isdigit() and int(inviter_id) != user_id:
                    inviter_id = int(inviter_id)
                    # Check if inviter exists in the database
                    conn = sqlite3.connect("utilisateurs.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM utilisateurs WHERE id = ?", (inviter_id,))
                    inviter = cursor.fetchone()
                    if inviter:
                        # Update inviter's balance and invite count
                        cursor.execute("UPDATE utilisateurs SET sold = sold + 500, invite = invite + 1 WHERE id = ?", (inviter_id,))
                        conn.commit()
                        # Fetch inviter's updated data
                        cursor.execute("SELECT sold, invite FROM utilisateurs WHERE id = ?", (inviter_id,))
                        inviter_data = cursor.fetchone()
                        if inviter_data:
                            sold, invite = inviter_data
                            # Notify inviter
                            await bot.send_message(
                                chat_id=inviter_id,
                                text=(
                                    f"🎉 Félicitations ! {user_name} a rejoint grâce à ton invitation.\n\n"
                                    f"💰 Ton solde a été augmenté de 500 FCFA. Solde actuel : {sold} FCFA\n"
                                    f"👥 Nombre d'invitations : {invite}"
                                )
                            )
                    conn.close()

                # Send a welcome message with the main menu
                await message.reply(
                    f"🎉 **Bienvenue à nouveau, {user_name} !** 👋\n\n"
                    "✅ **Vous avez maintenant accès à toutes les fonctionnalités du bot.**\n\n"
                    "👉 **Invitez vos amis pour commencer à gagner de l'argent.**\n\n"
                    "💲 Chaque personne invitée vous rapporte 500 FCFA.\n\n"
                    "Vous pouvez retirer 🏦 vos gains à partir de 32,000 FCFA.\n\n"
                    "Qu'est-ce que tu attends ? Clique sur 📨 Inviter.",
                    reply_markup=get_main_menu()
                )
            else:
                # Show subscription prompt for the second channel
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="📢 S'abonner à la chaîne",
                                url=SECOND_CHANNEL_LINK
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="✅ J'ai rejoint",
                                callback_data="check_subscription_second_channel"
                            )
                        ]
                    ]
                )
                await message.reply(
                    "🎉 **Bienvenue dans l'aventure des gains !** 💸\n\n"
                    "🌟 **Rejoignez notre chaîne exclusive pour accéder au bot et commencez à gagner de l'argent dès aujourd'hui !**\n\n"
                    "💰 **C'est simple : invitez vos amis et gagnez 500 FCFA pour chaque ami invité !** Plus vous partagez, plus vous gagnez ! 🚀\n\n"
                    "👉 [Rejoindre la chaîne maintenant](https://t.me/+oUsEqNov1vFkYzhk)\n\n"
                    "Après avoir rejoint, cliquez sur **✅ J'ai rejoint**.",
                    reply_markup=keyboard
                )
        else:
            # Show subscription prompt for the first channel
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📢 S'abonner à la chaîne",
                            url="https://t.me/yann_games"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="✅ J'ai rejoint",
                            callback_data="check_subscription"
                        )
                    ]
                ]
            )
            await message.reply(
                "🎉 **Bienvenue dans l'aventure des gains !** 💸\n\n"
                "🌟 **Rejoignez notre chaîne exclusive pour accéder au bot et commencez à gagner de l'argent dès aujourd'hui !**\n\n"
                "💰 **C'est simple : invitez vos amis et gagnez 500 FCFA pour chaque ami invité !** Plus vous partagez, plus vous gagnez ! 🚀\n\n"
                "👉 [Rejoindre la chaîne maintenant](https://t.me/yann_games)\n\n"
                "Après avoir rejoint, cliquez sur **✅ J'ai rejoint**.",
                reply_markup=keyboard
            )
    except TelegramAPIError as e:
        logging.error(f"Error checking channel membership: {e}")
        await message.reply(
            "🚨 **Erreur lors de la vérification. Veuillez réessayer plus tard.**"
        )

# Callback handler for subscription check
@router.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription(callback_query: types.CallbackQuery):
    # Create a CommandStart object with the necessary parameters
    command = CommandStart(args=None, conf=None)
    
    # Call `send_welcome` again to recheck subscription
    message = types.Message(
        message_id=callback_query.message.message_id,
        from_user=callback_query.from_user,
        chat=callback_query.message.chat,
        date=callback_query.message.date
    )
    await send_welcome(message, command)

# Callback handler for second channel subscription check
@router.callback_query(lambda c: c.data == "check_subscription_second_channel")
async def check_subscription_second_channel(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name

    try:
        # Check if the user is a member of the second channel
        member_second_channel = await bot.get_chat_member(chat_id=SECOND_CHANNEL_ID, user_id=user_id)
        if member_second_channel.status in ["member", "creator", "administrator"]:
            # Prompt the user to create a 1xbet account and enter their 9-digit ID
            await callback_query.message.reply(
                "🎉 **Félicitations !** Vous êtes maintenant membre de la deuxième chaîne.\n\n"
                "👉 **Veuillez créer un compte 1xbet si vous n'en avez pas déjà un.**\n\n"
                "🔢 **Entrez les 9 chiffres de votre ID 1xbet pour continuer.**"
            )
            await state.set_state(WithdrawalStates.waiting_for_1xbet_id)
        else:
            await callback_query.message.reply(
                "❌ **Vous n'êtes pas encore membre de la deuxième chaîne.**\n\n"
                "👉 [Rejoignez la chaîne maintenant](https://t.me/+oUsEqNov1vFkYzhk)\n\n"
                "Après avoir rejoint, cliquez sur **✅ J'ai rejoint**."
            )
    except TelegramAPIError as e:
        logging.error(f"Error checking second channel membership: {e}")
        await callback_query.message.reply(
            "🚨 **Erreur lors de la vérification. Veuillez réessayer plus tard.**"
        )

# Handle the 9-digit 1xbet ID
@router.message(WithdrawalStates.waiting_for_1xbet_id)
async def handle_1xbet_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_1xbet_id = message.text

    # Validate the 9-digit ID
    if user_1xbet_id.isdigit() and len(user_1xbet_id) == 9:
        # Add the user to the database if not already there
        add_user_to_db(user_id, user_name)

        # Notify the user of successful registration
        await message.reply(
            "🎉 **Félicitations !** Votre ID 1xbet a été enregistré avec succès.\n\n"
            "✅ **Vous avez maintenant accès à toutes les fonctionnalités du bot.**\n\n"
            "👉 **Invitez vos amis pour commencer à gagner de l'argent.**\n\n"
            "💲 Chaque personne invitée vous rapporte 500 FCFA.\n\n"
            "Vous pouvez retirer 🏦 vos gains à partir de 32,000 FCFA.\n\n"
            "Qu'est-ce que tu attends ? Clique sur 📨 Inviter.",
            reply_markup=get_main_menu()
        )

        # Clear the state
        await state.clear()
    else:
        await message.reply(
            "❌ **ID 1xbet invalide. Veuillez entrer les 9 chiffres de votre ID 1xbet.**"
        )

# Main button handler
@router.message(lambda message: message.text in ["💰 Solde", "🏦 Retirer", "📨 Inviter", "🎁 Bonus", "⚙️ Paramètre", "❓ Comment ça marche"])
async def handle_buttons(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # Handle different buttons
    if message.text == "🏦 Retirer":
        # Connect to the database and fetch user's balance
        conn = sqlite3.connect("utilisateurs
