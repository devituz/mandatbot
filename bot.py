import telebot
from telebot import types
from telebot.types import WebAppInfo

from models import User, Channel, session
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

API_TOKEN = '7223835990:AAGCgfT6jqaekgBzWQdBmLbNJVyBRdROIjw'
ADMIN = ['7321341340', '1769851684', '1239492923']
bot = telebot.TeleBot(API_TOKEN)
logging.basicConfig(level=logging.INFO)


def get_channels():
    return [channel.name for channel in session.query(Channel).all()]


def check_subscription(chat_id):
    channels = get_channels()
    not_subscribed_channels = []
    for channel in channels:
        try:
            member_status = bot.get_chat_member(channel, chat_id).status
            if member_status not in ['member', 'administrator', 'creator']:
                not_subscribed_channels.append(channel)
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Error checking subscription for {channel}: {e}")
            not_subscribed_channels.append(channel)
    return not_subscribed_channels


def prompt_subscription(chat_id, not_subscribed_channels):
    markup = types.InlineKeyboardMarkup()
    for channel in not_subscribed_channels:
        button = types.InlineKeyboardButton(text=f" ➕Obuna bo'lish", url=f"https://t.me/{channel[1:]}")
        markup.add(button)
    button_check = types.InlineKeyboardButton(text="Tekshirish", callback_data='check_subscription')
    markup.add(button_check)
    bot.send_message(chat_id, "Botimizdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                     reply_markup=markup)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle the /start command."""
    chat_id = message.chat.id
    first_name = message.chat.first_name
    last_name = message.chat.last_name

    user = session.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        user = User(chat_id=chat_id, first_name=first_name, last_name=last_name)
        session.add(user)
        session.commit()

    if str(chat_id) in ADMIN:
        bot.send_message(chat_id, "Admin tog'o sizga qanday yordam bera olaman!")
        show_main_menu(message)
    else:
        not_subscribed_channels = check_subscription(chat_id)
        if not_subscribed_channels:
            prompt_subscription(chat_id, not_subscribed_channels)
        else:
            bot.send_message(
                chat_id,
                "👋 Assalomu Alaykum! Botimiz orqali Mandat natijalarini bilishingiz mumkin.\n\n"
                "🆔 Abituriyentning Ruxsatnomadagi ID raqamini kiriting:"
            )


def fetch_data(entrant_id: str) -> List[Dict[str, str]]:
    url = 'https://mandat.uzbmb.uz/Bakalavr2024/MainSearch'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': '.AspNetCore.Antiforgery.UZ8z2jIqXdQ=CfDJ8CzSYY35RFBNm9xcyoWBJWduB53dTK8eOkDxun7SYJkiUCBhpYoU0i7m024MXQrXMuMIjXX_PC62cpBMxqghlQzhkx-h3SqP8cVx4WlTjyp5k5Ndw2Yd5PLkU-AMKh7Nk4q4ZUSVZEu9ZMFCsvulKTU',
        'Host': 'mandat.uzbmb.uz',
        'Origin': 'https://mandat.uzbmb.uz',
        'Referer': 'https://mandat.uzbmb.uz/Bakalavr2024/MainSearch',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
    }

    data = {
        'entrantid': entrant_id,
        "lang": "uz",
        '__RequestVerificationToken': 'CfDJ8CzSYY35RFBNm9xcyoWBJWd62nL7A7HUq8hEqi2QCWAG_gfdxgSady2qPAuCqpBkdJ9iFXAApTOGb7BZDCEeP7OljKjeNCYzCnS_snYd338apDzYRR46MVGvHvCKpYjylGCzzGPN-rYNABQxdOFyPLg'
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        table_info_rows = soup.find_all('tr', class_='table-info')

        results: List[Dict[str, str]] = []

        for row in table_info_rows:
            cells = row.find_all('td')
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            result = {
                'ruxsatnoma_id': cell_texts[0] if len(cell_texts) > 0 else '',
                'fish': cell_texts[1] if len(cell_texts) > 1 else '',
                'jamiball': cell_texts[2] if len(cell_texts) > 2 else '',
                'batafsil': f'https://mandat.uzbmb.uz{row.find("a", class_="btn btn-info")["href"]}' if row.find(
                    "a", class_="btn btn-info") else ''
            }

            results.append(result)

        return results
    else:
        return None


def show_main_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=False, resize_keyboard=True)
    chat_id = message.chat.id

    if str(chat_id) in ADMIN:
        button_send_message = telebot.types.KeyboardButton('✍️ Reklama')
        button_statistika = telebot.types.KeyboardButton('📊 Statistika')
        button_add_channel = telebot.types.KeyboardButton('🔧 Kanal qo\'shish')
        button_show_channels = telebot.types.KeyboardButton('📜 Kanallar ro\'yxati')
        markup.add(button_send_message, button_statistika, button_add_channel, button_show_channels)
        bot.send_message(chat_id, "Tugmalardan birini tanlang:", reply_markup=markup)
        bot.clear_step_handler_by_chat_id(chat_id)
    else:
        pass


@bot.callback_query_handler(func=lambda call: call.data == 'check_subscription')
def callback_check_subscription(call):
    chat_id = call.message.chat.id

    if str(chat_id) in ADMIN:
        show_main_menu(call.message)
    else:
        not_subscribed_channels = check_subscription(chat_id)

        if not_subscribed_channels:
            prompt_subscription(chat_id, not_subscribed_channels)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                                  text="👋 Assalomu Alaykum! Botimiz orqali Mandat natijalarini bilishingiz mumkin.\n\n"
                                       "🆔 Abituriyentning Ruxsatnomadagi ID raqamini kiriting:")
            # Foydalanuvchini ma'lumotlar bazasiga saqlash
            first_name = call.message.chat.first_name
            last_name = call.message.chat.last_name
            user = session.query(User).filter_by(chat_id=chat_id).first()
            if not user:
                user = User(chat_id=chat_id, first_name=first_name, last_name=last_name)
                session.add(user)
                session.commit()
            show_main_menu(call.message)


@bot.message_handler(func=lambda message: message.text == '📜 Kanallar ro\'yxati')
def handle_show_channels(message):
    if str(message.chat.id) not in ADMIN:
        bot.reply_to(message, "Sizga ruxsat berilmagan.")
        return

    try:
        channels = get_channels()
        if channels:
            markup = types.InlineKeyboardMarkup()
            for channel in channels:
                delete_button = types.InlineKeyboardButton(
                    text=f"❌ {channel}",
                    callback_data=f"delete_channel:{channel}"
                )
                markup.add(delete_button)

            bot.send_message(message.chat.id, "Kanallar ro'yxati:", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Hech qanday kanal mavjud emas.")
    except Exception as e:
        print(f"Error in handle_show_channels: {e}")
        bot.reply_to(message, 'Xatolik yuz berdi. Iltimos, qaytadan urinib ko‘ring.')


@bot.message_handler(func=lambda message: message.text == '🔧 Kanal qo\'shish')
def handle_add_channel(message):
    if str(message.chat.id) not in ADMIN:
        bot.reply_to(message, "Sizga ruxsat berilmagan.")
        return

    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    back_button = telebot.types.KeyboardButton('Orqaga qaytish')
    markup.add(back_button)
    bot.send_message(message.chat.id, "Yangi kanal manzilini kiriting: Misol uchun - @shohbozbekuz",
                     reply_markup=markup)
    bot.register_next_step_handler(message, process_add_channel)


def process_add_channel(message):
    if message.text == 'Orqaga qaytish':
        show_main_menu(message)
        return

    channel_name = message.text
    chat_id = message.chat.id

    try:
        chat_member = bot.get_chat_member(channel_name, bot.get_me().id)
        if chat_member.status not in ['administrator', 'creator']:
            bot.reply_to(message, f"Kanal yoki guruhda admin bo'lmaganligim sababli qo'sha olmayman: {channel_name}")
            ask_for_channel_name(message)
            return

        new_channel = Channel(name=channel_name)
        session.add(new_channel)
        session.commit()
        bot.send_message(chat_id, f"'{channel_name}' kanali qo'shildi.")
        show_main_menu(message)
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Error checking admin status for {channel_name}: {e}")
        bot.reply_to(message,
                     'Kanal yoki guruh mavjud emas yoki men admin emasman. Iltimos, to\'g\'ri manzilni kiriting.')
        ask_for_channel_name(message)
    except Exception as e:
        print(f"Error in process_add_channel: {e}")
        bot.reply_to(message, 'Xatolik yuz berdi. Iltimos, qaytadan urinib ko‘ring.')
        ask_for_channel_name(message)


def ask_for_channel_name(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    item = telebot.types.KeyboardButton("Orqaga qaytish")
    markup.add(item)
    bot.register_next_step_handler(message, process_add_channel)
    if message.text == 'Orqaga qaytish':
        show_main_menu(message)
        return


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_channel:'))
def handle_delete_channel(call):
    channel_name = call.data.split(':')[1]
    try:
        channel = session.query(Channel).filter_by(name=channel_name).first()
        if channel:
            session.delete(channel)
            session.commit()
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=f"'{channel_name}' kanali o'chirildi.")
        else:
            bot.answer_callback_query(call.id, f"'{channel_name}' kanali topilmadi.")
        # Ro'yxatni yangilash
        handle_show_channels(call.message)
    except Exception as e:
        print(f"Error in handle_delete_channel: {e}")
        bot.answer_callback_query(call.id, 'Xatolik yuz berdi. Iltimos, qaytadan urinib ko‘ring.')


@bot.message_handler(func=lambda message: message.text == '📊 Statistika')
def handle_statistics(message):
    if str(message.chat.id) not in ADMIN:
        bot.reply_to(message, "Sizga ruxsat berilmagan.")
        return

    try:
        users = session.query(User).all()
        total_users = len(users)
        active_users = 0
        blocked_users = 0
        not_subscribed_users = 0

        for user in users:
            try:
                if check_subscription(user.chat_id):
                    active_users += 1
                else:
                    not_subscribed_users += 1
            except telebot.apihelper.ApiTelegramException as e:
                print(f"Error checking user subscription for {user.chat_id}: {e}")
                blocked_users += 1

        # blocked_users = total_users - active_users - not_subscribed_users

        stat_message = (f"Jami foydalanuvchilar: {total_users}\n"
                        # f"Faol foydalanuvchilar: {active_users}\n"
                        # f"Bloklangan foydalanuvchilar: {blocked_users}\n"
                        f"Kanallarga obuna bo'lmagan foydalanuvchilar: {not_subscribed_users}")

        bot.send_message(message.chat.id, stat_message)
    except Exception as e:
        print(f"Error in handle_statistics: {e}")
        bot.reply_to(message, 'Xatolik yuz berdi. Iltimos, qaytadan urinib ko‘ring.')


@bot.message_handler(func=lambda message: message.text == '✍️ Reklama')
def handle_send_message_to_all(message):
    if str(message.chat.id) not in ADMIN:
        bot.reply_to(message, "Sizga ruxsat berilmagan.")
        return

    try:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        back_button = telebot.types.KeyboardButton('Orqaga qaytish')
        markup.add(back_button)
        bot.send_message(message.chat.id, "Xabarni, rasmni, musiqani, yoki faylni kiriting:", reply_markup=markup)
        bot.register_next_step_handler(message, process_send_message_to_all)
    except Exception as e:
        print(f"Error in handle_send_message_to_all: {e}")
        bot.reply_to(message, 'Xatolik yuz berdi. Iltimos, qaytadan urinib ko‘ring.')


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id

    if str(chat_id) not in ADMIN:
        not_subscribed_channels = check_subscription(chat_id)
        if not_subscribed_channels:
            prompt_subscription(chat_id, not_subscribed_channels)
            return  # End function execution if not subscribed

    entrant_id = message.text

    if entrant_id.isdigit():
        results = fetch_data(entrant_id)

        if results:
            for result in results:
                response_message = (
                    f"🆔 ID : {result['ruxsatnoma_id']}\n"
                    f"👤 F.I.O : {result['fish']}\n"
                    f"📊 To'plagan ball : {result['jamiball']}\n"
                )

                markup = telebot.types.InlineKeyboardMarkup()
                if result.get('batafsil'):  # Use get() to avoid KeyError
                    button = telebot.types.InlineKeyboardButton(
                        text="⚡️Batafsil",
                        web_app=telebot.types.WebAppInfo(url=result['batafsil'])
                    )
                    markup.add(button)

                bot.send_message(chat_id, response_message, reply_markup=markup)
    else:
        bot.send_message(
            chat_id,
            "Kechirasiz menga faqat abituriyentning Ruxsatnomadagi ID raqamini kiriting: "
        )
        show_main_menu(message)




def process_send_message_to_all(message):
    if message.text == 'Orqaga qaytish':
        show_main_menu(message)
        return

    try:
        users = session.query(User).all()

        success_count = 0
        failure_count = 0
        if message.content_type == 'text':
            for user in users:
                try:
                    bot.send_message(user.chat_id, message.text)
                    success_count += 1
                except Exception:
                    failure_count += 1
        elif message.content_type == 'photo':
            for user in users:
                try:
                    bot.send_photo(user.chat_id, message.photo[-1].file_id, caption=message.caption)
                    success_count += 1
                except Exception:
                    failure_count += 1
        elif message.content_type == 'audio':
            for user in users:
                try:
                    bot.send_audio(user.chat_id, message.audio.file_id, caption=message.caption)
                    success_count += 1
                except Exception:
                    failure_count += 1
        elif message.content_type == 'document':
            for user in users:
                try:
                    bot.send_document(user.chat_id, message.document.file_id, caption=message.caption)
                    success_count += 1
                except Exception:
                    failure_count += 1

        bot.send_message(message.chat.id, f"Xabar yuborildi.\n"
                                          f"Yuborilgan foydalanuvchilar: {success_count}\n"
                                          f"Xatolik yuz berilgan foydalanuvchilar: {failure_count}")
        show_main_menu(message)
    except Exception as e:
        print(f"Error in process_send_message_to_all: {e}")
        bot.reply_to(message, 'Xatolik yuz berdi. Iltimos, qaytadan urinib ko‘ring.')


def process_remove_channel(message):
    if message.text == 'Orqaga qaytish':
        show_main_menu(message)
        return

    channel_name = message.text
    try:
        channel = session.query(Channel).filter_by(name=channel_name).first()
        if channel:
            session.delete(channel)
            session.commit()
            bot.send_message(message.chat.id, f"'{channel_name}' kanali o'chirildi.")
        else:
            bot.send_message(message.chat.id, f"'{channel_name}' kanali topilmadi.")
        show_main_menu(message)
    except Exception as e:
        print(f"Error in process_remove_channel: {e}")
        bot.reply_to(message, 'Xatolik yuz berdi. Iltimos, qaytadan urinib ko‘ring.')


bot.polling()
