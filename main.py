import telebot
import signal
from telebot import types
from price import show_price
from reg_mas import register_massage  # Регистрация на массаж
from reminders import send_reminder, run_scheduler  # Напоминания
from notifications import notify_doctor_confirmation  # Уведомления для доктора
from keyboards import main_menu_markup
from menu import main_menu
from config import bot
import time
import threading
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
logger.info('Бот запущен')

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(
        message.chat.id,
        "Добро пожаловать! Выберите пункт из меню или напишите /help для справки:",
        reply_markup=main_menu_markup()
    )

@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.send_message(
        message.chat.id,
        'Вопросы, пожелания, предложения, проблемы можете направить разработчику на почту: yurjewivan@yandex.ru\n'
        'Спасибо за понимание.'    )
    main_menu(message)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.lower()
    try:
        if text == 'прайс':
            show_price(message)
        elif text == 'записаться':
            register_massage(message)
        else:
            bot.reply_to(
                message, 
                "Извините, я не понимаю ваш запрос. Выберите пункт из меню.",
                reply_markup=main_menu_markup()
            )
    except telebot.apihelper.ApiException as e:
        # Обработка ошибки API Telegram
        logger.error(f"Ошибка API Telegram: {e}")
        reconnect()

    except Exception as e:
        # Обработка других исключений
        logger.error(f"Ошибка: {e}")

# Функция для повторного подключения в случае ошибки
def reconnect():
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
            break  # Прерывание цикла, если подключение удалось
        except telebot.apihelper.ApiException as e:
            # Обработка ошибки API Telegram
            logger.error(f"Ошибка API Telegram: {e}")
            logger.info("Повторное подключение через 10 секунд...")
            time.sleep(10)
        except Exception as e:
            # Обработка других исключений
            logger.error(f"Ошибка при подключении: {e}")
            logger.info("Повторное подключение через 10 секунд...")
            time.sleep(10)

# Остановка бота при завершении работы
def exit_handler(signal, frame):
    logger.info("Остановка бота...")
    bot.stop_polling()

# Устанавливаем обработчик сигнала Ctrl+C
signal.signal(signal.SIGINT, exit_handler)

# Запуск фонового потока для напоминаний
threading.Thread(target=run_scheduler, daemon=True).start()

# Запуск бота
reconnect()