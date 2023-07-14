import telebot
import signal
from telebot import types
from price import show_price
from reg_mas import register_massage
from check_time import check_available_time
from keyboards import main_menu_markup
from menu import main_menu
from config import bot
import time
# инициализация бота

print('start')
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "Добро пожаловать! Выберите пункт из меню или напишите /help для справки:", reply_markup=main_menu_markup())

@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.send_message(message.chat.id, 'Вопросы, пожелания, предложения, проблемы, можете направить разработчику на почту: r1oaz@yandex.ru\n'
                     f'перед тем, как записываться на массаж, нажмите кнопку "проверить свободное время", иначе, может получиться так, что запишетесь вы и ещё кто-нибудь на одно и то же время\n'
                     f'спасибо за понимание.')
    main_menu(message)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.lower()
    try:
        if text == 'прайс':
            show_price(message)
        elif text == 'записаться':
            register_massage(message)
        elif text == 'проверить свободное время':
            check_available_time(message)
        else:
            bot.reply_to(message, "Извините, я не понимаю ваш запрос. Выберите пункт из меню.")
    except telebot.apihelper.ApiException as e:
        # Обработка ошибки API Telegram
        print(f"Ошибка API Telegram: {e}")
        reconnect()

    except Exception as e:
        # Обработка других исключений
        print(f"Ошибка: {e}")

# Функция для переподключения к API Telegram
def reconnect():
    while True:
        try:
            bot.polling(none_stop=True)

        except Exception as e:
            # Выводим сообщение об ошибке и ждем перед следующей попыткой подключения
            print(f"Ошибка при подключении: {e}")
            print("Повторное подключение через 10 секунд...")
            time.sleep(10)

def exit_handler(signal, frame):
    print("Остановка бота...")
    bot.stop_polling()

# Устанавливаем обработчик сигнала Ctrl+C
signal.signal(signal.SIGINT, exit_handler)

# Запускаем бота
bot.polling(none_stop=True)
