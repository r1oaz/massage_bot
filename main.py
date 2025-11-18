import telebot

import signal
from telebot import types
from price import show_price
from reg_mas import register_massage  # Регистрация на массаж
from reminders import restore_timers_from_db  # Напоминания (восстановление таймеров)
from notifications import notify_doctor_confirmation  # Уведомления для доктора
from keyboards import main_menu_markup
from utils import ensure_db
from menu import main_menu
from config import bot
import time
import threading
import logging
from logging.handlers import RotatingFileHandler
import sys
import os

# Настройка логирования: вывод в консоль и в файл out.log
root_logger = logging.getLogger()
# Очистим существующие хендлеры, чтобы не было дублей
for h in list(root_logger.handlers):
    root_logger.removeHandler(h)
root_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
# Use rotating file handler to avoid unlimited growth of out.log
log_path = os.path.join(os.path.dirname(__file__), 'out.log')
file_handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
file_handler.setFormatter(formatter)
root_logger.addHandler(stream_handler)
root_logger.addHandler(file_handler)
logger = logging.getLogger(__name__)

# Инициализация бота
logger.info('Бот запущен')

# Убедимся, что файл базы данных существует
ensure_db()

# Файлы-маркеры процесса: при старте — bot.running, при остановке — bot.stopped
BASE_DIR = os.path.dirname(__file__)
RUN_MARKER = os.path.join(BASE_DIR, 'bot.running')
STOP_MARKER = os.path.join(BASE_DIR, 'bot.stopped')

def _write_marker(path, text):
    # Пишем атомарно: сначала .tmp, затем os.replace
    try:
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception as e:
        logger.error(f"Ошибка записи маркера {path}: {e}")

# Удалим старый стоп-маркер (если есть) и создадим маркер запущенного процесса
try:
    if os.path.exists(STOP_MARKER):
        os.remove(STOP_MARKER)
except Exception:
    pass

try:
    _write_marker(RUN_MARKER, f"pid:{os.getpid()} started:{time.asctime()}")
except Exception:
    pass

# Обернём методы отправки сообщений бота для централизованного логирования
_orig_send = bot.send_message
_orig_reply = bot.reply_to
from utils import log_outgoing

def _send_and_log(chat_id, text, *args, **kwargs):
    try:
        log_outgoing(chat_id, text, **kwargs)
    except Exception:
        pass
    return _orig_send(chat_id, text, *args, **kwargs)

def _reply_and_log(message, text, *args, **kwargs):
    try:
        cid = getattr(getattr(message, 'chat', None), 'id', None)
        log_outgoing(cid, text, **kwargs)
    except Exception:
        pass
    return _orig_reply(message, text, *args, **kwargs)

bot.send_message = _send_and_log
bot.reply_to = _reply_and_log

# Флаг/событие для корректного завершения reconnect при Ctrl+C
stop_event = threading.Event()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(
        message.chat.id,
        "Добро пожаловать! Выберите пункт из меню или напишите /help для справки:",
        reply_markup=main_menu_markup(message.chat.id)
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
    text = (message.text or "").strip().lower()
    try:
        if text == 'прайс':
            show_price(message)
        elif text == 'записаться':
            register_massage(message)
        elif text == 'действия':
            # Показываем меню действий (отмена/перенос) если у пользователя есть запись
            from reminders import show_actions
            show_actions(message)
        else:
            bot.reply_to(
                message, 
                "Извините, я не понимаю ваш запрос. Выберите пункт из меню.",
                reply_markup=main_menu_markup(message.chat.id)
            )
    except telebot.apihelper.ApiException as e:
        # Обработка ошибки API Telegram
        logger.error(f"Ошибка API Telegram: {e}")
        reconnect()

def reconnect():
    """Бесконечный цикл polling, который уважает stop_event.
    Если stop_event установлен (например, Ctrl+C), функция выходит и не перезапускает polling.
    """
    while not stop_event.is_set():
        try:
            logger.info('Запуск polling...')
            bot.polling(none_stop=True, timeout=60)
            if stop_event.is_set():
                logger.info('stop_event установлен — прекращаем reconnect')
                break
            logger.info('Polling остановлен — повторный запуск через 10 секунд')
            time.sleep(10)
        except telebot.apihelper.ApiException as e:
            logger.error(f"Ошибка API Telegram: {e}")
            if stop_event.is_set():
                logger.info('stop_event установлен — прекращаем reconnect после ApiException')
                break
            logger.info("Повторное подключение через 10 секунд...")
            time.sleep(10)
            continue
        except Exception as e:
            logger.error(f"Ошибка при подключении: {e}")
            if stop_event.is_set():
                logger.info('stop_event установлен — прекращаем reconnect после Exception')
                break
            logger.info("Повторное подключение через 10 секунд...")
            time.sleep(10)
            continue

# Остановка бота при завершении работы
def exit_handler(signal, frame):
    logger.info("Остановка бота (Ctrl+C)...")
    # Устанавливаем флаг остановки — reconnect не должен перезапускать polling
    stop_event.set()
    try:
        bot.stop_polling()
    except Exception:
        pass
    # Завершаем процесс полностью
    logger.info("Выход из процесса по сигналу Ctrl+C")
    # Удаляем маркер running и создаём маркер stopped
    try:
        if os.path.exists(RUN_MARKER):
            os.remove(RUN_MARKER)
    except Exception:
        pass
    try:
        _write_marker(STOP_MARKER, f"pid:{os.getpid()} stopped:{time.asctime()} signal:SIGINT")
    except Exception:
        pass
    # Используем os._exit чтобы гарантированно остановить процесс и избежать
    # внутреннего перезапуска reconnect в текущем процессе.
    os._exit(0)

# Устанавливаем обработчик сигнала Ctrl+C
signal.signal(signal.SIGINT, exit_handler)

# Восстановим таймеры напоминаний из БД при старте
try:
    restore_timers_from_db()
except Exception:
    logger.exception("Не удалось восстановить таймеры при старте")

# Запуск бота
reconnect()