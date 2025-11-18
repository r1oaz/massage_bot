from config import bot, DOKTOR_ID
import openpyxl
from utils import excel_lock
import logging

logger = logging.getLogger(__name__)

# Функция для получения информации о пациенте по chat_id
def get_patient_info(chat_id):
    """Получает ФИО и телефон пациента по chat_id"""
    try:
        with excel_lock:
            wb = openpyxl.load_workbook('db.xlsx')
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                try:
                    if str(row[0]) == str(chat_id):
                        fio = row[1]
                        phone_number = row[2]
                        wb.close()
                        return fio, phone_number
                except Exception:
                    logger.debug(f"Ошибка при чтении строки в get_patient_info chat_id={chat_id}", exc_info=True)
                    continue
            wb.close()
    except Exception:
        pass
    return None, None

# Уведомление доктора о подтверждении визита
def notify_doctor_confirmation(chat_id, procedure_date, procedure_time, fio=None, phone_number=None):
    """Уведомляет доктора о подтверждении визита. fio и phone_number можно передать явно."""
    if not (fio and phone_number):
        fio, phone_number = get_patient_info(chat_id)
    if fio and phone_number:
        bot.send_message(
            DOKTOR_ID,
            f"Пациент <a href='tg://user?id={chat_id}'>{fio}</a> подтвердил визит на {procedure_date} в {procedure_time}.\n"
            f"Номер телефона: {phone_number}",
            parse_mode="HTML"
        )

# Уведомление доктора о новой записи на массаж
def notify_doctor_new_appointment(chat_id, fio, phone_number, massage_type, procedure_date, procedure_time):
    """Уведомляет доктора о новой записи на массаж"""
    if fio and phone_number and massage_type and procedure_date and procedure_time:
        bot.send_message(
            DOKTOR_ID,
            f"Новая запись на массаж:\n\n"
            f"Пациент: <a href='tg://user?id={chat_id}'>{fio}</a>\n"
            f"Номер телефона: {phone_number}\n"
            f"Тип массажа: {massage_type}\n"
            f"Дата: {procedure_date}\n"
            f"Время: {procedure_time}",
            parse_mode="HTML"
        )

# Уведомление доктора об отмене записи
def notify_doctor_cancellation(chat_id, procedure_date, procedure_time, fio=None, phone_number=None):
    """Уведомляет доктора об отмене записи. fio и phone_number можно передать явно."""
    if not (fio and phone_number):
        fio, phone_number = get_patient_info(chat_id)
    if fio and phone_number:
        bot.send_message(
            DOKTOR_ID,
            f"Пациент <a href='tg://user?id={chat_id}'>{fio}</a> отменил визит на {procedure_date} в {procedure_time}.\n"
            f"Номер телефона: {phone_number}",
            parse_mode="HTML"
        )

# Уведомление доктора о переносе записи на новую дату и время
def notify_doctor_reschedule(chat_id, fio, old_date, old_time, new_date, new_time, phone_number=None):
    """Уведомляет доктора о переносе записи. phone_number можно передать явно."""
    if not phone_number:
        phone_number = get_patient_info(chat_id)[1]
    if fio and phone_number and old_date and old_time and new_date and new_time:
        bot.send_message(
            DOKTOR_ID,
            f"Пациент <a href='tg://user?id={chat_id}'>{fio}</a> перенес визит.\n\n"
            f"Старое время: {old_date} в {old_time}\n"
            f"Новое время: {new_date} в {new_time}\n"
            f"Номер телефона: {phone_number}",
            parse_mode="HTML"
        )
