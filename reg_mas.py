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

logger = logging.getLogger(__name__)

def register_massage(message):
    """Запуск процесса записи на массаж"""
    from utils import log_incoming
    log_incoming(message)
    bot.send_message(message.chat.id, "Введите ФИО:", reply_markup=types.ReplyKeyboardRemove())
    # Регистрируем следующий шаг по chat_id для устойчивости
    bot.register_next_step_handler_by_chat_id(message.chat.id, ask_phone_number)

def ask_phone_number(message):
    from utils import log_incoming
    log_incoming(message)
    fio = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Отправить номер", request_contact=True))
    bot.send_message(
        message.chat.id,
        "Пожалуйста, отправьте свой номер телефона кнопкой ниже или введите его вручную:",
        reply_markup=keyboard
    )
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_phone_number, fio)

def handle_phone_number(message, fio):
    from utils import log_incoming
    log_incoming(message)
    if message.contact and message.contact.phone_number:
        phone_number = message.contact.phone_number
    else:
        phone_number = message.text
    bot.send_message(message.chat.id, "Выберите тип массажа:", reply_markup=massage_types_markup())
    bot.register_next_step_handler_by_chat_id(message.chat.id, ask_date_step, fio, phone_number)

def ask_massage_type(message, fio):
    # Устаревшая функция, не используется
    pass

def ask_date_step(message, fio, phone_number):
    massage_type = message.text
    from utils import ask_date
    from utils import log_incoming
    log_incoming(message)
    ask_date(message, fio, phone_number, massage_type, confirm_registration)

def confirm_registration(message, fio, phone_number, massage_type, date, old_date=None, old_time=None):
    """Подтверждение записи пользователем"""
    from utils import log_incoming
    log_incoming(message)
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
    # Регистрируем по chat_id, чтобы следующий ввод всегда попал в handler
    bot.register_next_step_handler_by_chat_id(message.chat.id, save_registration, fio, phone_number, massage_type, date, time_slot)

def save_registration(message, fio, phone_number, massage_type, date, time_slot):
    """Сохраняет запись в базе и уведомляет доктора"""
    from utils import log_incoming
    log_incoming(message)
    if (message.text or "").strip().lower() == 'да':
        try:
            from utils import excel_lock
            # Варианты напоминания: метки и минуты
            options = [
                ('5 минут', 5),
                ('30 минут', 30),
                ('1 час', 60),
                ('3 часа', 180),
                ('6 часов', 360),
                ('12 часов', 720),
                ('1 день', 1440),
            ]

            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for label, _ in options:
                kb.add(types.KeyboardButton(label))

            def finalize_registration(msg):
                choice = (msg.text or '').strip()
                mapping = {lbl: mins for lbl, mins in options}
                remind_before = mapping.get(choice, 180)
                try:
                    with excel_lock:
                        wb = openpyxl.load_workbook('db.xlsx')
                        sheet = wb.active
                        row = [msg.chat.id, fio, phone_number, massage_type, date, time_slot, remind_before]
                        logger.info(f"Запись в db.xlsx: chat_id={msg.chat.id} fio={fio} phone={phone_number} type={massage_type} date={date} time={time_slot} remind_before={remind_before}")
                        sheet.append(row)
                        wb.save('db.xlsx')
                        wb.close()
                    schedule_reminder(msg.chat.id, fio, date, time_slot, remind_before)
                    notify_doctor_new_appointment(msg.chat.id, fio, phone_number, massage_type, date, time_slot)
                    bot.send_message(msg.chat.id, "Запись сохранена. Ждем вас!", reply_markup=types.ReplyKeyboardRemove())
                    main_menu(msg)
                except Exception as e:
                    logger.error(f"Ошибка при окончательном сохранении записи: {e}")
                    bot.send_message(msg.chat.id, "Произошла ошибка при сохранении записи. Попробуйте еще раз.", reply_markup=types.ReplyKeyboardRemove())
                    register_massage(msg)

            bot.send_message(message.chat.id, 'За сколько напомнить о процедуре?', reply_markup=kb)
            bot.register_next_step_handler_by_chat_id(message.chat.id, finalize_registration)
        except Exception as e:
            logger.error(f"Ошибка при сохранении записи: {e}")
            bot.send_message(message.chat.id, "Произошла ошибка при сохранении записи. Попробуйте еще раз.", reply_markup=types.ReplyKeyboardRemove())
            register_massage(message)
    else:
        register_massage(message)