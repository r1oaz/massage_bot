import telebot
from config import Token
from time import sleep
bot = telebot.TeleBot(Token)
while True:
    print('starting...')
    try:
        bot.polling(none_stop=True, interval=0)
    except KeyboardInterrupt:
        with open("exit.log", "w", encoding="UTF-8") as f:
            f.write("exited!")
        exit()
    except telebot.apihelper.ApiException:
        print('Проверьте связь и API')
        sleep(10)
    except Exception as e:
        print(e)
        sleep(15)