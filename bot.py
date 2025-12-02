import telebot
import threading
import datetime
import json
import os

lock = threading.Lock()

with open("token.txt", 'r') as fin:
    token = fin.read()
bot = telebot.TeleBot(token)

try:
    with open("./logs/chats.json", 'r') as fin:
        chats = json.load(fin)
except Exception:
    chats = {}

@bot.message_handler(content_types=["text"])
def handle_text_message(message):
    if message.from_user.username not in chats:
        chats[message.from_user.username] = message.chat.id
        with open("./logs/chats.json", 'w') as fout:
            json.dump(chats, fout)

    now = datetime.datetime.now()
    dir_path = f"./logs/text_from_{message.from_user.username}_{now.date()}_{now.hour}_{now.minute}_{now.second}_{now.microsecond}"
    os.mkdir(dir_path)
    with open(f"{dir_path}/message.json", 'w') as fout:
        json.dump(message.json, fout)

    with open(f"{dir_path}/text", 'w') as fout:
        fout.write(message.text)

    bot.send_message(message.chat.id, "Асалам алеекум, брат. Две тысячи семьсот рублей отдолжи на лирику и два тропа")



@bot.message_handler(content_types=["photo"])
def handle_photo_message(message):
    # lock.acquire()
    if message.from_user.username not in chats:
        chats[message.from_user.username] = message.chat.id
        with open("./logs/chats.json", 'w') as fout:
            json.dump(chats, fout)

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

    bot.send_message(message.chat.id, "Асалам алеекум, брат. Две тысячи семьсот рублей отдолжи на лирику и два тропа")

    # lock.release()

@bot.message_handler(content_types=["sticker"])
def handle_sticker_message(message):
    if message.from_user.username not in chats:
        chats[message.from_user.username] = message.chat.id
        with open("./logs/chats.json", 'w') as fout:
            json.dump(chats, fout)

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

    bot.send_message(message.chat.id, "Асалам алеекум, брат. Две тысячи семьсот рублей отдолжи на лирику и два тропа")



bot.polling(none_stop=True, interval=0)




