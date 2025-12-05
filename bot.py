from threading import Thread, Lock
from uuid import uuid4
import urllib.parse as parse
import telebot
import datetime
import json
import os
from telebot import types
from enum import Enum
import torch
from transformers import DeepseekV2ForCausalLM, AutoTokenizer, GenerationConfig, RobertaTokenizerFast, RobertaModel
from embedding_system.make_db import make_db
from sqlalchemy import create_engine
from embedding_system.embedding_system import EmbeddingSystem
from embedding_system.db_crud import DBCrud
from crawler import observe_directory_daemon


print("Up question model")
llm_name = "deepseek-ai/DeepSeek-V2-Lite"
question_device = torch.device("cuda:0")

question_model = DeepseekV2ForCausalLM.from_pretrained(llm_name, dtype=torch.bfloat16)
question_model.generation_config = GenerationConfig.from_pretrained(llm_name)
question_model.generation_config.pad_token_id = question_model.generation_config.eos_token_id
question_model = question_model.to(question_device)
question_model.eval()

question_tokenizer = AutoTokenizer.from_pretrained(llm_name)

print("Up search model")
search_tokenizer = RobertaTokenizerFast.from_pretrained("FacebookAI/roberta-large")
vocab_size = len(search_tokenizer.get_vocab())

d_model = 1024
search_limit = 10

padding_index = search_tokenizer.pad_token_type_id
search_device = torch.device("cuda:0")
search_dtype = torch.float16


search_model = RobertaModel.from_pretrained("FacebookAI/roberta-large", dtype=search_dtype).to(search_device)

make_db(d_model)

print("Up db")
db_engine = create_engine("postgresql://postgres:ValhalaWithZolinks@localhost:5432/postgres")
db_crud = DBCrud(db_engine)
EmbeddingSystem.class_init(search_tokenizer, search_model, db_crud)

print("Up crawler")
directory_to_check = "C:/Users/amis-/PycharmProjects/bot/files"
observe_directory_daemon(directory_to_check)


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
    dir_path = f"./logs/json_only_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}_message_uuid_{uuid_}"

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


def process_db_select_results(query_results):

    results_to_show = []
    for i, query_result_row in enumerate(query_results):
        results_to_show.append(
            f"- {i}) ###{query_result_row.document_name}###\n{query_result_row.snippet}"
        )
    return results_to_show


def search(message):
    result_list = process_db_select_results(
        EmbeddingSystem.handle_user_query(d_model, message.text, search_limit)
    )
    bot.send_message(message.chat.id, "\n".join(result_list))



def handle_search_query(message, cancel_markup_message_id):
    if message.content_type == "text":
        bot.edit_message_reply_markup(message.chat.id, cancel_markup_message_id)

        save_query_thread = Thread(target=save_search_query_message_logs, args=(message,), daemon=True)
        save_query_thread.start()

        bot.send_message(message.chat.id, f"Обрабатываю Ваш запрос...")

        search(message)


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

def answer_user_question(text):
    with torch.no_grad():
        input_tensor = search_tokenizer(text, return_tensors="pt").input_ids.to(question_device)

        output_gen = question_model.generate(input_tensor, max_new_tokens=128)

        answer = search_tokenizer.decode(output_gen[0][input_tensor.shape[1]:], skip_special_tokens=True)
    return answer


def handle_question_query(message, cancel_markup_message_id):
    if message.content_type == "text":
        bot.edit_message_reply_markup(message.chat.id, cancel_markup_message_id)
        bot.send_message(message.chat.id, "Я думаю над вашим вопросом, это может занять некоторое время...")
        answer = answer_user_question(message.text)
        bot.send_message(message.chat.id, answer)

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

try:
    del chats["w0rmixChep"]
except Exception:
    pass

print("Polling bot")
bot.polling(none_stop=True, interval=0)




