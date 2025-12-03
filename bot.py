from threading import Thread, Lock
from uuid import uuid4
import telebot
import datetime
import json
import os
from telebot import types
from enum import Enum

class CallbackEnum(Enum):
    START = "/start"
    SEARCH = "Поиск в базе данных"
    QUESTION = "Задать вопрос"
    MACHMALA = "Мачмала"
    CANCEL = "Отмена"
    CANCEL_SYSTEM_VALUE = "/cancel"


chats_dict_lock = Lock()

with open("token.txt", 'r') as fin:
    token = fin.read()
bot = telebot.TeleBot(token)

try:
    with open("./logs/chats.json", 'r') as fin:
        chats = json.load(fin)
except Exception:
    chats = {}


def log_message(message):
    if message.content_type == "text":
        log_thread = Thread(target=save_text_message_logs, args=(message,), daemon=True)
        log_thread.start()
    elif message.content_type == "photo":
        log_thread = Thread(target=save_photo_message_logs, args=(message,), daemon=True)
        log_thread.start()
    elif message.content_type == "sticker":
        log_thread = Thread(target=save_sticker_message_logs, args=(message,), daemon=True)
        log_thread.start()
    else:
        log_thread = Thread(target=save_message_json_only, args=(message,), daemon=True)
        log_thread.start()


def save_message_json_only(message):
    uuid_ = uuid4().hex
    now = datetime.datetime.now()
    dir_path = f"./logs/text_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}_message_uuid_{uuid_}"

    try:
        os.mkdir(dir_path)
    except FileExistsError as ex:
        print(f"{dir_path} already exists")

    with open(f"{dir_path}/message.json", 'w') as fout:  # TODO thread???
        json.dump(message.json, fout)


def save_search_query_message_logs(message):
    uuid_ = uuid4().hex
    now = datetime.datetime.now()
    dir_path = f"./logs/search_query_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}_message_uuid_{uuid_}"

    try:
        os.mkdir(dir_path)
    except FileExistsError as ex:
        print(f"{dir_path} already exists")

    with open(f"{dir_path}/message.json", 'w') as fout:  # TODO thread???
        json.dump(message.json, fout)

    with open(f"{dir_path}/text.txt", 'w') as fout:  # TODO thread???
        fout.write(message.text)


def handle_search_query(message, cancel_markup_message_id):
    if message.content_type == "text":
        bot.edit_message_reply_markup(message.chat.id, cancel_markup_message_id)

        save_query_thread = Thread(target=save_search_query_message_logs, args=(message,), daemon=True)
        save_query_thread.start()

        print(f"Search query: {message.text}")
        bot.send_message(message.chat.id, f"был введен запрос:{message.text}")

        send_question(message)
    else:
        log_message(message)

        bot.edit_message_reply_markup(message.chat.id, cancel_markup_message_id)
        markup = types.InlineKeyboardMarkup()
        item_cancel = types.InlineKeyboardButton(CallbackEnum.CANCEL.value, callback_data=CallbackEnum.CANCEL_SYSTEM_VALUE.value)
        markup.row(item_cancel)
        cancel_markup_message_id = bot.send_message(message.chat.id, "Поисковый запрос должен быть текстовым сообщением", reply_markup=markup).id

        bot.register_next_step_handler(message, handle_search_query, cancel_markup_message_id)


@bot.callback_query_handler(lambda call: call.data == CallbackEnum.CANCEL_SYSTEM_VALUE.value)
def cancel_callback(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.id)
    bot.send_message(call.message.chat.id, "Выбор отменен")
    bot.clear_step_handler(call.message)
    send_question(call.message)


def search_handler(message):
    remove = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Поисковой запрос представляет собой текстовое сообщение", reply_markup=remove)

    markup = types.InlineKeyboardMarkup()
    item_cancel = types.InlineKeyboardButton(CallbackEnum.CANCEL.value, callback_data=CallbackEnum.CANCEL_SYSTEM_VALUE.value)
    markup.row(item_cancel)
    cancel_markup_message_id = bot.send_message(message.chat.id, "Введите Ваш поисковый запрос", reply_markup=markup).id

    bot.register_next_step_handler(message, handle_search_query, cancel_markup_message_id)


def save_question_query_message_logs(message, answer):
    uuid_ = uuid4().hex
    now = datetime.datetime.now()
    dir_path = f"./logs/question_query_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}_message_uuid_{uuid_}"

    try:
        os.mkdir(dir_path)
    except FileExistsError as ex:
        print(f"{dir_path} already exists")

    with open(f"{dir_path}/message.json", 'w') as fout:  # TODO thread???
        json.dump(message.json, fout)

    with open(f"{dir_path}/question.txt", 'w') as fout:  # TODO thread???
        fout.write(message.text)

    with open(f"{dir_path}/answer.txt", 'w') as fout:  # TODO thread???
        fout.write(answer)


def handle_question_query(message, cancel_markup_message_id):
    if message.content_type == "text":
        bot.edit_message_reply_markup(message.chat.id, cancel_markup_message_id)
        print(f"Question query: {message.text}")
        bot.send_message(message.chat.id, f"был задан вопрос:{message.text}")

        answer = f"Question query: {message.text}"  # TODO temp
        save_question_thread = Thread(target=save_question_query_message_logs, args=(message, answer), daemon=True)
        save_question_thread.start()

        send_question(message)
    else:
        log_message(message)

        bot.edit_message_reply_markup(message.chat.id, cancel_markup_message_id)
        markup = types.InlineKeyboardMarkup()
        item_cancel = types.InlineKeyboardButton(CallbackEnum.CANCEL.value, callback_data=CallbackEnum.CANCEL_SYSTEM_VALUE.value)
        markup.row(item_cancel)

        cancel_markup_message_id = bot.send_message(message.chat.id, "Вопрос должен быть задан текстовым сообщением", reply_markup=markup).id
        bot.register_next_step_handler(message, handle_question_query, cancel_markup_message_id)


def question_handler(message):
    remove = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Вопрос представляет собой текстовое сообщение", reply_markup=remove)

    markup = types.InlineKeyboardMarkup()
    item_cancel = types.InlineKeyboardButton(CallbackEnum.CANCEL.value, callback_data=CallbackEnum.CANCEL_SYSTEM_VALUE.value)
    markup.row(item_cancel)
    cancel_markup_message_id = bot.send_message(message.chat.id, "Задавайте Ваш вопрос", reply_markup=markup).id

    bot.register_next_step_handler(message, handle_question_query, cancel_markup_message_id)


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
        log_message(message)
        bot.register_next_step_handler(message, handle_user_answer)


def send_question(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_search = types.KeyboardButton(CallbackEnum.SEARCH.value)
    item_question = types.KeyboardButton(CallbackEnum.QUESTION.value)
    item_machmala = types.KeyboardButton(CallbackEnum.MACHMALA.value)
    markup.row(item_search, item_question, item_machmala)
    bot.send_message(message.chat.id, "Выберите необходимое Вам действие", reply_markup=markup)
    bot.register_next_step_handler(message, handle_user_answer)


def save_chats(chats):
    chats_dict_lock.acquire()
    with open("./logs/chats.json", 'w') as fout:
        json.dump(chats, fout)
    chats_dict_lock.release()

def save_text_message_logs(message):
    uuid_ = uuid4().hex
    now = datetime.datetime.now()
    dir_path = f"./logs/text_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}_message_uuid_{uuid_}"

    try:
        os.mkdir(dir_path)
    except FileExistsError as ex:
        print(f"{dir_path} already exists")

    with open(f"{dir_path}/message.json", 'w') as fout:  # TODO thread???
        json.dump(message.json, fout)

    with open(f"{dir_path}/text.txt", 'w') as fout:  # TODO thread???
        fout.write(message.text)

def define_username(message):
    # if message.from_user.last_name is not None:
    #     return f"{message.from_user.first_name} {message.from_user.last_name}"
    # else:
        return f"@{message.from_user.username}"

@bot.message_handler(content_types=["text"])
def handle_text_message (message):
    if message.from_user.username not in chats or message.text == CallbackEnum.START.value:
        chats[message.from_user.username] = message.chat.id

        save_chats_thread = Thread(target=save_chats, args=(chats,), daemon=True)
        save_chats_thread.start()

        bot.send_message(message.chat.id, f"Здравствуйте, {define_username(message)}")
        send_question(message)
    # elif message.text == CallbackEnum.START.value:
    #     send_question(message)

    save_logs_thread = Thread(target=save_text_message_logs, args=(message,), daemon=True)
    save_logs_thread.start()
    #bot.send_message(message.chat.id, "Асалам алеекум, брат. Две тысячи семьсот рублей отдолжи на лирику и два тропа")


def save_photo_message_logs(message):
    uuid_ = uuid4().hex
    now = datetime.datetime.now()
    dir_path = f"./logs/photo_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}_message_uuid_{uuid_}"

    photo_id = message.photo[-1].file_id
    photo_file = bot.get_file(photo_id)
    photo_extension = photo_file.file_path.split(".")[-1]

    photo = bot.download_file(photo_file.file_path)

    os.mkdir(dir_path)
    with open(f"{dir_path}/message.json", 'w') as fout:  # TODO thread???
        json.dump(message.json, fout)

    if message.caption:
        with open(f"{dir_path}/caption.txt", 'w') as fout:  # TODO thread???
            fout.write(message.caption)

    with open(f"{dir_path}/file.{photo_extension}", 'wb') as fout:  # TODO thread???
        fout.write(photo)


@bot.message_handler(content_types=["photo"])
def handle_photo_message(message):
    if message.from_user.username not in chats:
        chats[message.from_user.username] = message.chat.id

        save_chats_thread = Thread(target=save_chats, args=(chats,), daemon=True)
        save_chats_thread.start()

        bot.send_message(message.chat.id, f"Здравствуйте, {define_username(message)}")
        send_question(message)

    save_logs_thread = Thread(target=save_photo_message_logs, args=(message,), daemon=True)
    save_logs_thread.start()




def save_sticker_message_logs(message):
    uuid_ = uuid4().hex
    now = datetime.datetime.now()
    dir_path = f"./logs/sticker_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}_message_uuid_{uuid_}"

    stick_id = message.sticker.file_id
    stick_file = bot.get_file(stick_id)
    stick_extension = stick_file.file_path.split(".")[-1]
    stick = bot.download_file(stick_file.file_path)

    os.mkdir(dir_path)
    with open(f"{dir_path}/message.json", 'w') as fout:  # TODO thread???
        json.dump(message.json, fout)

    with open(f"{dir_path}/sticker.{stick_extension}", 'wb') as fout:  # TODO thread???
        fout.write(stick)


@bot.message_handler(content_types=["sticker"])
def handle_sticker_message(message):
    if message.from_user.username not in chats:
        chats[message.from_user.username] = message.chat.id

        save_chats_thread = Thread(target=save_chats, args=(chats,), daemon=True)
        save_chats_thread.start()

        bot.send_message(message.chat.id, f"Здравствуйте, {define_username(message)}")
        #send_question(message)

        send_question(message)
    save_logs_thread = Thread(target=save_sticker_message_logs, args=(message,), daemon=True)
    save_logs_thread.start()

del chats["w0rmixChep"]

bot.polling(none_stop=True, interval=0)




