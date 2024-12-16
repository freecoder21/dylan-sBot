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
    waiting_for_1xbet_id = State()

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
    conn = sqlite3.connect("utilisateurs.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY,
            nom TEXT,
            sold REAL DEFAULT 0.0,
            invite INTEGER DEFAULT 0
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

# Function to generate the main menu keyboard
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 Solde"),
                KeyboardButton(text="🏦 Retirer"),
            ],
            [
                KeyboardButton(text="📨 Inviter"),
                KeyboardButton(text="🎁 Bonus"),
                KeyboardButton(text="⚙️ Paramètre"),
            ],
            [
                KeyboardButton(text="❓ Comment ça marche"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

# Update the send_welcome function
from aiogram.filters.command import CommandStart

@router.message(CommandStart())
async def send_welcome(message: types.Message, command: CommandStart, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    inviter_id = command.args

    # Initial Subscription Check
    await check_all_subscriptions(message, state, inviter_id)


# Combined subscription check function
async def check_all_subscriptions(message: types.Message, state: FSMContext, inviter_id=None):
     user_id = message.from_user.id
     user_name = message.from_user.first_name

     try:
        # Check membership of the first channel
        member_first_channel = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member_first_channel.status not in ["member", "creator", "administrator"]:
            # Prompt to join first channel
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ J'ai rejoint",
                            callback_data="check_subscription_first_channel"
                        )
                    ]
                ]
            )
            await message.reply(
                "🎉 **Bienvenue dans l'aventure des gains !** 💸\n\n"
                "🌟 **Rejoignez notre première chaîne exclusive pour accéder au bot et commencez à gagner de l'argent dès aujourd'hui !**\n\n"
                "💰 **C'est simple : invitez vos amis et gagnez 500 FCFA pour chaque ami invité !** Plus vous partagez, plus vous gagnez ! 🚀\n\n"
                "👉 [Rejoindre la chaîne maintenant](https://t.me/yann_games)\n\n"
                "Après avoir rejoint, cliquez sur **✅ J'ai rejoint**.",
                reply_markup=keyboard
            )
            return

        # Check membership of the second channel
        member_second_channel = await bot.get_chat_member(chat_id=SECOND_CHANNEL_ID, user_id=user_id)
        if member_second_channel.status not in ["member", "creator", "administrator"]:
            # Prompt to join second channel
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ J'ai rejoint",
                            callback_data="check_subscription_second_channel"
                        )
                    ]
                ]
            )
            await message.reply(
                "🎉 **Félicitations, vous avez rejoint la première chaine !** 🎉\n\n"
                "🌟 **Rejoignez notre deuxième chaîne exclusive pour commencer à gagner de l'argent dès aujourd'hui !**\n\n"
                "💰 **C'est simple : invitez vos amis et gagnez 500 FCFA pour chaque ami invité !** Plus vous partagez, plus vous gagnez ! 🚀\n\n"
                "👉 [Rejoindre la chaîne maintenant](https://t.me/+oUsEqNov1vFkYzhk)\n\n"
                "Après avoir rejoint, cliquez sur **✅ J'ai rejoint**.",
                reply_markup=keyboard
            )
            return

        # If both are member proceed to database add
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
      
        # Both channels are joined - proceed to request 1xbet ID
        await message.reply(
            "🎉 **Félicitations !** Vous avez rejoint les deux chaînes.\n\n"
            "👉 **Veuillez créer un compte 1xbet si vous n'en avez pas déjà un.**\n\n"
            "🔢 **Entrez les 9 chiffres de votre ID 1xbet pour continuer.**"
        )
        await state.set_state(WithdrawalStates.waiting_for_1xbet_id)

     except TelegramAPIError as e:
         logging.error(f"Error checking channel membership: {e}")
         await message.reply(
             "🚨 **Erreur lors de la vérification. Veuillez réessayer plus tard.**"
         )


# Callback handler for first channel subscription check
@router.callback_query(lambda c: c.data == "check_subscription_first_channel")
async def check_subscription_first_channel(callback_query: types.CallbackQuery, state: FSMContext):
     # Create a CommandStart object with the necessary parameters
    command = CommandStart(args=None, conf=None)
    
    # Call `send_welcome` again to recheck subscription
    message = types.Message(
        message_id=callback_query.message.message_id,
        from_user=callback_query.from_user,
        chat=callback_query.message.chat,
        date=callback_query.message.date
    )
    await check_all_subscriptions(message,state)

# Callback handler for second channel subscription check
@router.callback_query(lambda c: c.data == "check_subscription_second_channel")
async def check_subscription_second_channel(callback_query: types.CallbackQuery, state: FSMContext):
  # Create a CommandStart object with the necessary parameters
    command = CommandStart(args=None, conf=None)
    
    # Call `send_welcome` again to recheck subscription
    message = types.Message(
        message_id=callback_query.message.message_id,
        from_user=callback_query.from_user,
        chat=callback_query.message.chat,
        date=callback_query.message.date
    )
    await check_all_subscriptions(message,state)


# Handle the 9-digit 1xbet ID
@router.message(WithdrawalStates.waiting_for_1xbet_id)
async def handle_1xbet_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_1xbet_id = message.text

    # Validate the 9-digit ID
    if user_1xbet_id.isdigit() and len(user_1xbet_id) == 9:

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
        conn = sqlite3.connect("utilisateurs.db")
        cursor = conn.cursor()
        cursor.execute("SELECT sold FROM utilisateurs WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            user_balance = user_data[0]  # Fetch balance
            if user_balance >= 32000:  # Minimum balance for withdrawal
                # Notify user to provide their phone number
                await message.reply(
                    "🎉 **Félicitations, vous avez atteint le montant minimum pour un retrait !** 💸\n\n"
                    "Veuillez entrer votre numéro de téléphone pour effectuer le retrait. 📞"
                )

                # Set state to wait for phone number
                await state.set_state(WithdrawalStates.waiting_for_phone_number)
            else:
                # Notify user of insufficient balance
                await message.reply(
                    "❌ **Désolé, votre solde est insuffisant pour un retrait.**\n\n"
                    f"💰 **Votre solde actuel :** {user_balance} FCFA\n"
                    f"👉 **Montant minimum requis :** 32,000 FCFA\n\n"
                    "Continuez à inviter des amis pour accumuler plus de gains ! 🚀"
                )
        else:
            # Notify user if they are not found in the database
            await message.reply(
                "❌ **Erreur : Vous n'êtes pas enregistré dans notre base de données.**\n\n"
                "Veuillez redémarrer le bot en utilisant la commande /start."
            )
    elif message.text == "💰 Solde":
        
        # Connect to the database
        conn = sqlite3.connect("utilisateurs.db")
        cursor = conn.cursor()
        
        # Fetch the user's balance and the number of invited friends
        cursor.execute("SELECT sold, invite FROM utilisateurs WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            user_balance, invited_friends = user_data
            await message.reply(
                f"👋 Hey {user_name},\n\n"
                f"💰 **Votre solde actuel :** {user_balance} FCFA\n"
                f"🤝 **Nombre d'amis invités :** {invited_friends} 🎉\n\n"
                "Merci de votre participation et continuez à inviter pour accumuler plus de gains ! 🚀"
            )
        else:
            await message.reply("❌ **Vous n'êtes pas enregistré dans notre base de données.**")

    elif message.text == "📨 Inviter":
       # Generate a unique referral link for the user
       referral_link = f"https://t.me/bigfortunateBot?start={user_id}"
    
       await message.reply(
        f"📨 **Invitez vos amis et gagnez !**\n\n"
        f"👥 Partagez votre lien d'invitation unique :\n\n"
        f"👉 [Cliquez ici pour copier votre lien](https://t.me/share/url?url={referral_link})\n\n"
        f"💰 Gagnez **500 FCFA** pour chaque ami qui s'inscrit via votre lien ! 🚀"
      )
    elif message.text == "🎁 Bonus":
        user_id = message.from_user.id
        user_name = message.from_user.first_name
    
        # Connect to the database
        conn = sqlite3.connect("utilisateurs.db")
        cursor = conn.cursor()
    
        # Check if the user has already claimed the bonus
        cursor.execute("SELECT sold, invite FROM utilisateurs WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
    
        if user_data:
            user_balance, invite_count = user_data
    
            # Check if the bonus has already been claimed (assuming bonus claimed flag is stored)
            if user_balance > 0:  # Replace with a proper check if using a separate 'bonus_claimed' field
                # Bonus already claimed
                await message.reply(
                    f"🔒 Désolé {user_name}, vous avez déjà réclamé votre bonus. 😅\n\n"
                    "💡 Mais ne vous inquiétez pas, vous pouvez toujours gagner de l'argent en invitant vos amis ! 🤝\n\n"
                    "Invitez et gagnez **500 FCFA** pour chaque nouvel ami. 🎯"
                )
            else:
                # Add bonus to the user's balance
                new_balance = user_balance + 300
                cursor.execute("UPDATE utilisateurs SET sold = ? WHERE id = ?", (new_balance, user_id))
                conn.commit()
    
                await message.reply(
                    f"🎉 Félicitations {user_name} !\n\n"
                    f"💸 Vous avez obtenu un bonus de **300 FCFA** ajouté à votre solde. 🤑\n\n"
                    "Continuez à profiter de l'aventure et gagnez encore plus en invitant vos amis ! 🚀"
                )
        else:
            # User not found in the database
            await message.reply(
                "🚨 Une erreur s'est produite. Veuillez vous assurer que vous êtes inscrit. 🛠️"
            )

            # Close the database connection
            conn.close()

    elif message.text == "⚙️ Paramètre":
        
        # Connect to the database
        conn = sqlite3.connect("utilisateurs.db")
        cursor = conn.cursor()
        
        # Fetch user data
        cursor.execute("SELECT nom, sold, invite FROM utilisateurs WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            user_name, solde, invites = user_data
            await message.reply(
                f"👋 Bonjour, {user_name} !\n\n"
                f"🔢 ID : {user_id} \n\n"
                f"💰 Solde actuel : {solde} FCFA \n\n"
                f"👥 Nombre d'invitations : {invites} \n\n"
                "🌟 Vous voulez gagner encore plus d'argent ?\n\n"
                "Invitez vos amis à nous rejoindre ! Plus vous invitez, plus vous gagnez ! 🎉💸\n\n"
                "🔗 Partagez votre lien dès maintenant ! \n\n"
                "Merci et à bientôt ! 🙌"
            )
        else:
            await message.reply("❌ **Vous n'êtes pas enregistré dans notre base de données.**")
    elif message.text == "❓ Comment ça marche":
        await message.reply(
            "❓ **Comment ça marche**\n\n"
            "1️⃣ Invitez vos amis à rejoindre le bot.\n"
            "2️⃣ Gagnez 500 FCFA par ami inscrit.\n"
            "3️⃣ Retirez vos gains dès que vous atteignez 32,000 FCFA.\n\n"
            "📈 Plus vous invitez, plus vous gagnez !"
        )

@router.message(WithdrawalStates.waiting_for_phone_number)
async def handle_phone_number(message: types.Message, state: FSMContext):
    phone_number = message.text
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # Validate phone number
    if phone_number.isdigit() and len(phone_number) >= 10:
        # Connect to the database
        conn = sqlite3.connect("utilisateurs.db")
        cursor = conn.cursor()

        # Update the database with the phone number
        cursor.execute(
            "UPDATE utilisateurs SET sold = sold - 32000 WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()

        # Send a confirmation message to the channel
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"📢 **Demande de Retrait** 💵\n\n"
                f"👤 **Nom :** {user_name}\n"
                f"💰 **Solde :** 32,000 FCFA\n"
                f"📱 **Mode de Paiement :** Paiement Mobile\n"
                f"📞 **Numéro de Téléphone :** {phone_number}\n\n"
                f"✅ **Veuillez traiter cette demande de paiement.**"
            )
        )

        # Notify the user of the successful withdrawal process
        await message.reply(
            "✅ **Votre demande de retrait a été soumise avec succès !** 💸\n\n"
            "Un message a été envoyé à l'administrateur. Vous recevrez votre paiement sous peu. Merci ! 🙏"
        )

        # Clear the state
        await state.clear()
    else:
        await message.reply(
            "❌ **Numéro de téléphone invalide. Veuillez entrer un numéro valide.**"
        )

# Set bot commands
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Démarrer le bot"),
    ]
    await bot.set_my_commands(commands)

# Main application setup
# List of random names, IDs, phone numbers, and payment methods
random_names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Heidi", "Ivan", "Judy"]
random_ids = [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010]
random_phone_numbers = ["1234567890", "2345678901", "3456789012", "4567890123", "5678901234", "6789012345", "7890123456", "8901234567", "9012345678", "0123456789"]
payment_methods = ["Orange Money", "Mobile Money", "Moove Money"]

async def send_random_withdrawal_approval():
    while True:
        # Generate random data
        name = random.choice(random_names)
        user_id = random.choice(random_ids)
        phone_number = random.choice(random_phone_numbers)
        payment_method = random.choice(payment_methods)
        balance = random.randint(32000, 100000)

        # Send the message to the channel
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"📢 **Demande de Retrait Approuvée** 💵\n\n"
                f"👤 **Nom :** {name}\n"
                f"🆔 **ID :** {user_id}\n"
                f"💰 **Solde :** {balance} FCFA\n\n"
                f"📱 **Mode de Paiement :** {payment_method}\n"
                f"📞 **Numéro de Téléphone :** {phone_number}\n\n"
                f"✅ **Le paiement a été effectué avec succès.**"
            )
        )

        # Wait for 1 minute before sending the next message
        await asyncio.sleep(60)

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    await set_commands(bot)
    init_db()
    # asyncio.create_task(send_random_withdrawal_approval())


async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    init_db()
    dp = Dispatcher()
    dp.include_router(router)
    print("bot.....")
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)

if __name__ == "__main__":
    main()
