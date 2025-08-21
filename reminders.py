import time
from telebot import types
from config import bot, doktor_id
import schedule
import datetime
import threading
import openpyxl
import logging
from notifications import notify_doctor_cancellation, notify_doctor_reschedule, notify_doctor_confirmation
from utils import ask_date, ask_time

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_reminder(chat_id, procedure_date, procedure_time):
    """Отправляет напоминание пациенту"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Подтвердить посещение", "Отменить запись", "Перенести запись")
    reminder_message = f"Напоминание: Ваша процедура назначена на {procedure_date} в {procedure_time}."
    bot.send_message(chat_id, reminder_message, reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(chat_id, handle_reminder_response, procedure_date, procedure_time)

def handle_reminder_response(message, procedure_date, procedure_time):
    """Обрабатывает ответ пациента на напоминание"""
    chat_id = message.chat.id
    response = message.text.lower()
    if response == "подтвердить посещение":
        notify_doctor_confirmation(chat_id, procedure_date, procedure_time)
        bot.send_message(chat_id, "Спасибо, мы вас ждем!")
    elif response == "отменить запись":
        if cancel_appointment(chat_id):
            notify_doctor_cancellation(chat_id, procedure_date, procedure_time)
            bot.send_message(chat_id, "Ваша запись отменена.")
            show_main_menu(chat_id)
        else:
            bot.send_message(chat_id, "Не удалось отменить запись. Попробуйте еще раз.")
    elif response == "перенести запись":
        bot.send_message(chat_id, "Выберите новую дату:", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, ask_date_for_reschedule, procedure_date, procedure_time)

def ask_date_for_reschedule(message, old_date, old_time):
    """Запрашивает новую дату для переноса записи"""
    fio = "Пациент"
    phone_number = "Номер телефона"
    ask_date(message, fio, phone_number, "Тип массажа", reschedule_appointment, old_date, old_time)

def ask_time_for_reschedule(message, fio, phone_number, old_date, old_time):
    new_date = message.text
    ask_time(message, fio, phone_number, "Тип массажа", reschedule_appointment, new_date, old_date, old_time)

def reschedule_appointment(message, fio, phone_number, massage_type, new_date, old_date, old_time):
    """Переносит запись на новую дату и время"""
    new_time = message.text
    chat_id = message.chat.id
    try:
        from utils import excel_lock
        with excel_lock:
            if update_appointment(chat_id, new_date, new_time):
                notify_doctor_reschedule(chat_id, fio, old_date, old_time, new_date, new_time)
                bot.send_message(chat_id, "Ваша запись перенесена.")
            else:
                bot.send_message(chat_id, "Не удалось перенести запись. Попробуйте еще раз.")
    except Exception as e:
        logger.error(f"Ошибка при переносе записи: {e}")
        bot.send_message(chat_id, "Ошибка при переносе записи. Попробуйте еще раз.")
    show_main_menu(chat_id)

def cancel_appointment(chat_id):
    """Отменяет запись пациента"""
    try:
        from utils import excel_lock
        with excel_lock:
            wb = openpyxl.load_workbook("db.xlsx")
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2):
                if row[0].value == chat_id:
                    sheet.delete_rows(row[0].row, 1)
                    wb.save("db.xlsx")
                    wb.close()
                    return True
            wb.close()
        return False
    except Exception as e:
        logger.error(f"Ошибка при отмене записи: {e}")
        return False

def update_appointment(chat_id, new_date, new_time):
    """Обновляет дату и время записи пациента"""
    try:
        from utils import excel_lock
        with excel_lock:
            wb = openpyxl.load_workbook("db.xlsx")
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2):
                if row[0].value == chat_id:
                    row[4].value = new_date
                    row[5].value = new_time
                    wb.save("db.xlsx")
                    wb.close()
                    return True
            wb.close()
        return False
    except Exception as e:
        logger.error(f"Ошибка при обновлении записи: {e}")
        return False

def schedule_reminder(chat_id, fio, procedure_date, procedure_time):
    reminder_time = datetime.datetime.strptime(f"{procedure_date} {procedure_time}", "%d.%m.%Y %H:%M") - datetime.timedelta(hours=3)
    schedule.every().day.at(reminder_time.strftime("%H:%M")).do(
        send_reminder, chat_id, procedure_date, procedure_time
    )

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=run_scheduler, daemon=True).start()

def show_main_menu(chat_id):
    from menu import main_menu
    main_menu(types.SimpleNamespace(chat=types.SimpleNamespace(id=chat_id)))