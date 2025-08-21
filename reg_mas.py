import openpyxl
from telebot import types
from keyboards import massage_types_markup
from menu import main_menu
from config import bot
from notifications import notify_doctor_new_appointment  # Подключаем уведомления доктора
from reminders import schedule_reminder  # Подключаем напоминания из reminders.py
from date_utils import is_valid_date, is_weekend, check_date_format
from utils import ask_date, ask_time, get_available_times
import logging
import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_massage(message):
    """Запуск процесса записи на массаж"""
    bot.send_message(message.chat.id, "Введите ФИО:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, ask_phone_number)

def ask_phone_number(message):
    fio = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Отправить номер", request_contact=True))
    bot.send_message(
        message.chat.id,
        "Пожалуйста, отправьте свой номер телефона кнопкой ниже или введите его вручную:",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(message, handle_phone_number, fio)

def handle_phone_number(message, fio):
    if message.contact and message.contact.phone_number:
        phone_number = message.contact.phone_number
    else:
        phone_number = message.text
    bot.send_message(message.chat.id, "Выберите тип массажа:", reply_markup=massage_types_markup())
    bot.register_next_step_handler(message, ask_date_step, fio, phone_number)

def ask_massage_type(message, fio):
    # Устаревшая функция, не используется
    pass

def ask_date_step(message, fio, phone_number):
    massage_type = message.text
    from utils import ask_date
    ask_date(message, fio, phone_number, massage_type, confirm_registration)

def confirm_registration(message, fio, phone_number, massage_type, date, old_date=None, old_time=None):
    """Подтверждение записи пользователем"""
    time_slot = message.text
    bot.send_message(
        message.chat.id,
        f"Подтвердите запись:\n\n"
        f"ФИО: {fio}\n"
        f"Номер телефона: {phone_number}\n"
        f"Тип массажа: {massage_type}\n"
        f"Дата: {date}\n"
        f"Время: {time_slot}",
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
            types.KeyboardButton("Да"), types.KeyboardButton("Нет")
        )
    )
    bot.register_next_step_handler(message, save_registration, fio, phone_number, massage_type, date, time_slot)

def save_registration(message, fio, phone_number, massage_type, date, time_slot):
    """Сохраняет запись в базе и уведомляет доктора"""
    if message.text.lower() == 'да':
        try:
            import threading
            from utils import excel_lock
            with excel_lock:
                wb = openpyxl.load_workbook('db.xlsx')
                sheet = wb.active
                row = [message.chat.id, fio, phone_number, massage_type, date, time_slot]
                sheet.append(row)
                wb.save('db.xlsx')
                wb.close()
            schedule_reminder(message.chat.id, fio, date, time_slot)
            notify_doctor_new_appointment(message.chat.id, fio, phone_number, massage_type, date, time_slot)
            bot.send_message(message.chat.id, "Запись сохранена. Ждем вас!", reply_markup=types.ReplyKeyboardRemove())
            main_menu(message)
        except Exception as e:
            logger.error(f"Ошибка при сохранении записи: {e}")
            bot.send_message(message.chat.id, "Произошла ошибка при сохранении записи. Попробуйте еще раз.", reply_markup=types.ReplyKeyboardRemove())
            register_massage(message)
    else:
        register_massage(message)