import telebot
import threading
import datetime
import json
import os
from telebot import types
from enum import Enum

class CallbackEnum(Enum):
    SEARCH = "Поиск в базе данных"
    QUESTION = "Задать вопрос"
    MACHMALA = "Мачмала"


lock = threading.Lock()

with open("token.txt", 'r') as fin:
    token = fin.read()
bot = telebot.TeleBot(token)

try:
    with open("./logs/chats.json", 'r') as fin:
        chats = json.load(fin)
except Exception:
    chats = {}


def search_handler(message):
    remove = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Введите Ваш поисковый запрос", reply_markup=remove)
    # TODO handle
    bot.send_message(message.chat.id, "Тут нужно зарегать, что именно поиск")
    send_question(message)


def question_handler(message):
    remove = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Задавайте Ваш вопрос", reply_markup=remove)
    # TODO handle
    bot.send_message(message.chat.id, "Тут нужно зарегать, что именно вопрос")
    send_question(message)


def machmala_handler(message):
    remove = types.ReplyKeyboardRemove()
    try:
        with open("vera.jpg", 'rb') as fin:
            photo = fin.read()

            bot.send_photo(message.chat.id, photo, reply_markup=remove)
    except Exception:
        bot.send_message(message.chat.id, "мачмала", reply_markup=remove)
    #if message.from_user.username == "St_Kek_OParis" or message.from_user.username == "w0rmixChep":
    with open("stas.png", 'rb') as fin:
        photo = fin.read()
        bot.send_photo(message.chat.id, photo)
    send_question(message)


def handle_user_answer(message):
    if message.text == CallbackEnum.SEARCH.value:
        search_handler(message)
    elif message.text == CallbackEnum.QUESTION.value:
        question_handler(message)
    elif message.text == CallbackEnum.MACHMALA.value:
        machmala_handler(message)
    else:
        bot.register_next_step_handler(message, handle_user_answer)


def send_question(message):
    if message.from_user.last_name is not None:
        name = message.from_user.last_name
    else:
        name = f"@{message.from_user.username}"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_search = types.KeyboardButton(CallbackEnum.SEARCH.value)
    item_question = types.KeyboardButton(CallbackEnum.QUESTION.value)
    item_machmala = types.KeyboardButton(CallbackEnum.MACHMALA.value)
    markup.row(item_search, item_question, item_machmala)
    bot.send_message(message.chat.id, f"Здраствуйте, {name}. Выберите необходимое Вам действие", reply_markup=markup)
    bot.register_next_step_handler(message, handle_user_answer)


@bot.message_handler(content_types=["text"])
def handle_text_message (message):
    if message.from_user.username not in chats:
        chats[message.from_user.username] = message.chat.id

        # TODO thread
        with open("./logs/chats.json", 'w') as fout:
            json.dump(chats, fout)
        #
        send_question(message)


    # TODO thread
    now = datetime.datetime.now()
    dir_path = f"./logs/text_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}"
    os.mkdir(dir_path)

    with open(f"{dir_path}/message.json", 'w') as fout:
        json.dump(message.json, fout)

    with open(f"{dir_path}/text", 'w') as fout:
        fout.write(message.text)
    #
    #bot.send_message(message.chat.id, "Асалам алеекум, брат. Две тысячи семьсот рублей отдолжи на лирику и два тропа")



@bot.message_handler(content_types=["photo"])
def handle_photo_message(message):

    if message.from_user.username not in chats:
        chats[message.from_user.username] = message.chat.id
        # TODO thread
        with open("./logs/chats.json", 'w') as fout:
            json.dump(chats, fout)
        #

    # TODO thread
    now = datetime.datetime.now()
    dir_path = f"./logs/photo_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}"

    photo_id = message.photo[-1].file_id
    photo_file = bot.get_file(photo_id)
    photo_extension = photo_file.file_path.split(".")[-1]

    photo = bot.download_file(photo_file.file_path)


    os.mkdir(dir_path)
    with open(f"{dir_path}/message.json", 'w') as fout:
        json.dump(message.json, fout)

    if message.caption:
        with open(f"{dir_path}/caption.txt", 'w') as fout:
            fout.write(message.caption)

    with open(f"{dir_path}/file.{photo_extension}", 'wb') as fout:
        fout.write(photo)
    #
    send_question(message)


@bot.message_handler(content_types=["sticker"])
def handle_sticker_message(message):
    if message.from_user.username not in chats:
        chats[message.from_user.username] = message.chat.id
        # TODO thread
        with open("./logs/chats.json", 'w') as fout:
            json.dump(chats, fout)
        #

    # TODO thread
    now = datetime.datetime.now()
    dir_path = f"./logs/sticker_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}"

    stick_id = message.sticker.file_id
    stick_file = bot.get_file(stick_id)
    stick_extension = stick_file.file_path.split(".")[-1]
    stick = bot.download_file(stick_file.file_path)

    os.mkdir(dir_path)
    with open(f"{dir_path}/message.json", 'w') as fout:
        json.dump(message.json, fout)

    with open(f"{dir_path}/sticker.{stick_extension}", 'wb') as fout:
        fout.write(stick)
    #
    send_question(message)

del chats["w0rmixChep"]

bot.polling(none_stop=True, interval=0)




