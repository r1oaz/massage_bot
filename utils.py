import datetime
import openpyxl
import logging
from telebot import types
from config import bot
from date_utils import is_valid_date, is_weekend

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ask_date(message, fio, phone_number, massage_type, next_step_handler, old_date=None, old_time=None):
    """Показывает клавиатуру с датами для записи"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    today = datetime.date.today()
    for i in range(7):
        date = today + datetime.timedelta(days=i)
        if not is_weekend(date):
            keyboard.add(date.strftime("%d.%m.%Y"))
    bot.send_message(message.chat.id, "Выберите дату:", reply_markup=keyboard)
    bot.register_next_step_handler(message, ask_time, fio, phone_number, massage_type, next_step_handler, old_date, old_time)

def ask_time(message, fio, phone_number, massage_type, next_step_handler, date, old_date=None, old_time=None):
    """Показывает клавиатуру с доступным временем для выбранной даты"""
    date = message.text
    if not is_valid_date(date):
        bot.send_message(message.chat.id, "Неверная дата. Выберите дату из предложенных.", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, ask_date, fio, phone_number, massage_type, next_step_handler, old_date, old_time)
        return

    available_times = get_available_times(date)
    if available_times:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for time in available_times:
            keyboard.add(time)
        bot.send_message(message.chat.id, "Выберите время:", reply_markup=keyboard)
        bot.register_next_step_handler(message, next_step_handler, fio, phone_number, massage_type, date, old_date, old_time)
    else:
        bot.send_message(message.chat.id, "Нет свободного времени. Выберите другой день.", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, ask_date, fio, phone_number, massage_type, next_step_handler, old_date, old_time)

import threading
excel_lock = threading.Lock()

def get_available_times(date):
    """Возвращает список доступного времени для записи на выбранную дату"""
    fixed_times = [f"{hour:02d}:{minute:02d}" for hour in range(9, 18) for minute in (0, 30)]
    booked_times = []
    try:
        with excel_lock:
            wb = openpyxl.load_workbook('db.xlsx')
            sheet = wb.active
            booked_times = [row[5].value for row in sheet.iter_rows(min_row=2) if row[4].value == date]
            wb.close()
    except Exception as e:
        logger.error(f"Ошибка при чтении файла db.xlsx: {e}")
        return []

    available_times = [time for time in fixed_times if time not in booked_times]

    # Фильтрация времени для сегодняшней даты
    if date == datetime.date.today().strftime("%d.%m.%Y"):
        now = datetime.datetime.now()
        # Округление до ближайшего получаса
        minutes = now.minute
        if minutes < 30:
            next_time = now.replace(minute=30, second=0, microsecond=0)
        else:
            next_time = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        next_half_hour = next_time.strftime("%H:%M")
        available_times = [time for time in available_times if time >= next_half_hour]

    return available_times