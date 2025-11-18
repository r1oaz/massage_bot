import time
from telebot import types
from types import SimpleNamespace
from config import bot, DOKTOR_ID
import datetime
import threading
import openpyxl
import logging
from notifications import notify_doctor_cancellation, notify_doctor_reschedule, notify_doctor_confirmation
from utils import ask_date, ask_time

logger = logging.getLogger(__name__)
DEBUG_RESCHEDULE = False

# Таймеры для одноразовых напоминаний: key = row_num (int) или (chat_id,row,date,time) tuple
active_timers = {}
active_timers_lock = threading.RLock()

def _send_reminder_job_timer(chat_id, row_key, fio, phone, procedure_date, procedure_time):
    """Отправка напоминания из threading.Timer; вызывается в отдельном потоке."""
    try:
        send_reminder(chat_id, procedure_date, procedure_time)
    except Exception:
        logger.exception(f"Ошибка при выполнении timer-reminder for {row_key}")
    finally:
        # после выполнения удаляем таймер из словаря
        try:
            with active_timers_lock:
                active_timers.pop(row_key, None)
        except Exception:
            logger.exception("Ошибка при удалении записи таймера после срабатывания")

def schedule_one_off(row_key, send_dt, chat_id, fio, phone, procedure_date, procedure_time):
    """Запланировать одноразовый reminder через threading.Timer.
    row_key: уникальный ключ для записи (например row_num)
    send_dt: datetime.datetime когда нужно сработать
    """
    try:
        with active_timers_lock:
            # отменим старый таймер, если есть
            old = active_timers.get(row_key)
            if old:
                try:
                    old.cancel()
                except Exception:
                    logger.debug(f"Не удалось отменить старый таймер для {row_key}", exc_info=True)
            now = datetime.datetime.now()
            delay = (send_dt - now).total_seconds()
            if delay <= 0:
                # если время уже наступило — запустить немедленно в новом потоке
                threading.Thread(target=_send_reminder_job_timer, args=(chat_id, row_key, fio, phone, procedure_date, procedure_time), daemon=True).start()
                return
            t = threading.Timer(delay, _send_reminder_job_timer, args=(chat_id, row_key, fio, phone, procedure_date, procedure_time))
            t.daemon = True
            active_timers[row_key] = t
            t.start()
            logger.info(f"Запланировано одноразовое напоминание key={row_key} at {send_dt.isoformat()}")
    except Exception:
        logger.exception("Ошибка при schedule_one_off")

def cancel_timer_by_row(row_key):
    try:
        with active_timers_lock:
            t = active_timers.pop(row_key, None)
            if t:
                try:
                    t.cancel()
                    logger.info(f"Таймер отменён для {row_key}")
                except Exception:
                    logger.exception(f"Не удалось отменить таймер для {row_key}")
    except Exception:
        logger.exception("Ошибка в cancel_timer_by_row")

def restore_timers_from_db():
    """Прочитать `db.xlsx` и восстановить таймеры для будущих напоминаний.
    Использует колонку remind_before (минуты) и row_num как ключ.
    """
    try:
        from utils import excel_lock
        import os
        with excel_lock:
            if not os.path.exists('db.xlsx'):
                return
            wb = openpyxl.load_workbook('db.xlsx')
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2):
                try:
                    row_num = row[0].row
                    chat = row[0].value
                    fio = row[1].value
                    phone = row[2].value
                    date_str = row[4].value
                    time_str = row[5].value
                    remind_before = int(row[6].value) if (row[6].value is not None) else 180
                    if not (date_str and time_str and chat):
                        continue
                    base_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
                    send_dt = base_dt - datetime.timedelta(minutes=remind_before)
                    if send_dt > datetime.datetime.now():
                        schedule_one_off(row_num, send_dt, chat, fio, phone, date_str, time_str)
                except Exception:
                    logger.debug("Ошибка при восстановлении таймера для строки", exc_info=True)
                    continue
            wb.close()
    except Exception:
        logger.exception("Ошибка при restore_timers_from_db")
def send_reminder(chat_id, procedure_date, procedure_time):
    """Отправляет напоминание пациенту"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Подтвердить посещение", "Отменить запись", "Перенести запись")
    reminder_message = f"Напоминание: Ваша процедура назначена на {procedure_date} в {procedure_time}."
    bot.send_message(chat_id, reminder_message, reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(chat_id, handle_reminder_response, procedure_date, procedure_time)


def send_reminder_job(chat_id, procedure_date, procedure_time):
    pass


def show_actions(message):
    """Показывает список записей пользователя и позволяет выбрать одну для действий.
    Меню: список записей (строка содержит row_num|date time — type — fio) и кнопка 'Назад'.
    После выбора — показывается подробная карточка записи с опциями Перенести/Отменить/Назад.
    """
    chat_id = message.chat.id
    try:
        from utils import excel_lock
        with excel_lock:
            wb = openpyxl.load_workbook('db.xlsx')
            sheet = wb.active
            rows = []
            for row in sheet.iter_rows(min_row=2):
                try:
                    if str(row[0].value) == str(chat_id):
                        # Не показываем номер строки пользователю, формируем читаемую метку
                        date_val = row[4].value
                        time_val = row[5].value
                        mtype = row[3].value
                        fio = row[1].value
                        label = f"{date_val} {time_val} — {mtype} — {fio}"
                        rows.append(label)
                except Exception:
                    logger.debug("Ошибка при чтении строки в show_actions", exc_info=True)
                    continue
            wb.close()
    except Exception as e:
        logger.error(f"Ошибка при получении записи для действий: {e}")
        bot.send_message(chat_id, "Ошибка при проверке записи. Попробуйте позже.")
        return

    if not rows:
        bot.send_message(chat_id, "У вас нет активных записей.", reply_markup=types.ReplyKeyboardRemove())
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for label in rows:
        markup.add(label)
    markup.add("Назад")
    bot.send_message(chat_id, "Ваши записи: выберите запись для действий или нажмите Назад.", reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(chat_id, handle_appointments_list_selection)

def handle_reminder_response(message, procedure_date, procedure_time):
    """Обрабатывает ответ пациента на напоминание"""
    from utils import log_incoming
    log_incoming(message)
    chat_id = message.chat.id
    response = (message.text or "").strip().lower()
    if response == "подтвердить посещение":
        notify_doctor_confirmation(chat_id, procedure_date, procedure_time)
        bot.send_message(chat_id, "Спасибо, мы вас ждем!", reply_markup=types.ReplyKeyboardRemove())
        show_main_menu(chat_id)
    elif response == "отменить запись":
        if cancel_appointment(chat_id):
            notify_doctor_cancellation(chat_id, procedure_date, procedure_time)
            bot.send_message(chat_id, "Ваша запись отменена.")
            show_main_menu(chat_id)
        else:
            bot.send_message(chat_id, "Не удалось отменить запись. Попробуйте еще раз.")
    elif response == "перенести запись":
        # Сразу показываем клавиатуру выбора даты и запускаем flow переноса
        # Получим текущие данные записи и запустим ask_date напрямую
        from utils import get_appointment_by_chat
        info = get_appointment_by_chat(chat_id)
        if not info:
            bot.send_message(chat_id, "Не удалось найти вашу запись для переноса.", reply_markup=types.ReplyKeyboardRemove())
            show_main_menu(chat_id)
            return
        fio, phone_number, massage_type, date_val, time_val, row_num = info
        ask_date(message, fio or "Пациент", phone_number or "", massage_type or "", reschedule_appointment, date_val, time_val)

def ask_date_for_reschedule(message, old_date, old_time):
    """Запрашивает новую дату для переноса записи"""
    from utils import log_incoming, get_appointment_by_chat
    log_incoming(message)
    chat_id = message.chat.id
    info = get_appointment_by_chat(chat_id)
    if not info:
        bot.send_message(chat_id, "Не удалось найти вашу запись для переноса.", reply_markup=types.ReplyKeyboardRemove())
        show_main_menu(chat_id)
        return
    fio, phone_number, massage_type, date_val, time_val, row_num = info
    # Запрос даты, передаём реальные fio/phone/massage_type
    ask_date(message, fio or "Пациент", phone_number or "", massage_type or "", reschedule_appointment, old_date, old_time)

def ask_time_for_reschedule(message, fio, phone_number, massage_type, old_date, old_time):
    new_date = message.text
    ask_time(message, fio, phone_number, massage_type or "", reschedule_appointment, new_date, old_date, old_time)

def reschedule_appointment(message, fio, phone_number, massage_type, new_date, old_date, old_time):
    """Переносит запись на новую дату и время"""
    from utils import log_incoming
    log_incoming(message)
    new_time = message.text
    chat_id = message.chat.id
    try:
        from utils import excel_lock, get_appointment_by_chat
        # Работаем с конкретной записью — debug-сообщение отключено
        with excel_lock:
            logger.info(f"Попытка перенести запись chat_id={chat_id} {old_date} {old_time} -> {new_date} {new_time}")
            success = update_appointment(chat_id, new_date, new_time)
            if success:
                logger.info(f"Перенос успешно выполнен для chat_id={chat_id}")
                try:
                    notify_doctor_reschedule(chat_id, fio, old_date, old_time, new_date, new_time)
                except Exception:
                    logger.exception("notify_doctor_reschedule failed")
                bot.send_message(chat_id, "Ваша запись перенесена.")
            else:
                logger.warning(f"Не удалось перенести запись для chat_id={chat_id}")
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
                try:
                    if str(row[0].value) == str(chat_id):
                        # сохраним данные для уведомления доктора
                        row_num = row[0].row
                        old_date = row[4].value
                        old_time = row[5].value
                        fio = row[1].value
                        phone = row[2].value
                        # отменим таймер для этой записи, если он есть
                        try:
                            cancel_timer_by_row(row_num)
                        except Exception:
                            logger.exception(f"Не удалось отменить таймер для row={row_num}")
                        # удаляем запись, но у нас есть данные пациента для уведомления
                        sheet.delete_rows(row_num, 1)
                        wb.save("db.xlsx")
                        wb.close()
                        try:
                            notify_doctor_cancellation(chat_id, old_date, old_time, fio=fio, phone_number=phone)
                        except Exception:
                            logger.exception("notify_doctor_cancellation failed in cancel_appointment")
                        return True
                except Exception:
                    continue
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
                try:
                    cell_id = row[0].value
                    if str(cell_id) == str(chat_id):
                        row_num = row[0].row
                        old_date = row[4].value
                        old_time = row[5].value
                        # Попытка прочитать remind_before, если нет - оставить 180 минут
                        try:
                            remind_before = int(row[6].value) if row[6].value is not None else 180
                        except Exception:
                            remind_before = 180
                        fio = row[1].value
                        logger.info(f"Найдена строка {row_num} для chat_id={chat_id}: old_date={old_date} old_time={old_time} remind_before={remind_before}")
                        # отменим старый таймер по строке перед обновлением
                        try:
                            cancel_timer_by_row(row_num)
                        except Exception:
                            logger.exception(f"Не удалось отменить таймер для row={row_num} перед обновлением")
                        row[4].value = new_date
                        row[5].value = new_time
                        wb.save("db.xlsx")
                        wb.close()
                        logger.info(f"Обновление выполнено: row={row_num} new_date={new_date} new_time={new_time}")
                        # Перепланируем напоминание с учётом remind_before
                        try:
                            schedule_reminder(chat_id, fio, new_date, new_time, remind_before)
                        except Exception:
                            logger.exception("Не удалось перепланировать напоминание после update_appointment")
                        return True
                except Exception:
                    logger.exception("Ошибка при обработке строки в update_appointment")
                    continue
            wb.close()
        logger.warning(f"Запись для chat_id={chat_id} не найдена при update_appointment")
        return False
    except Exception as e:
        logger.exception(f"Ошибка при обновлении записи: {e}")
        return False

def schedule_reminder(chat_id, fio, procedure_date, procedure_time, remind_before_minutes=180):
    """Планирует напоминание за remind_before_minutes минут до процедуры."""
    try:
        base_dt = datetime.datetime.strptime(f"{procedure_date} {procedure_time}", "%d.%m.%Y %H:%M")
        reminder_dt = base_dt - datetime.timedelta(minutes=remind_before_minutes)
        # Используем одноразовый timer по row (или chat_id). Здесь попытаемся найти row для chat_id
        try:
            from utils import excel_lock
            with excel_lock:
                wb = openpyxl.load_workbook('db.xlsx')
                sheet = wb.active
                row_key = None
                for row in sheet.iter_rows(min_row=2):
                    try:
                        if str(row[0].value) == str(chat_id) and str(row[4].value) == str(procedure_date) and str(row[5].value) == str(procedure_time):
                            row_key = row[0].row
                            fio = row[1].value
                            phone = row[2].value
                            break
                    except Exception:
                        continue
                wb.close()
        except Exception:
            row_key = None
            fio = None
            phone = None

        # Если не нашли row_key — используем tuple (chat_id, date, time) как ключ
        key = row_key if row_key is not None else (chat_id, procedure_date, procedure_time)
        schedule_one_off(key, reminder_dt, chat_id, fio, phone, procedure_date, procedure_time)
    except Exception:
        logger.exception("Ошибка при планировании напоминания")

# Планировщик заменён на таймеры; восстановление таймеров выполняется из main.py при старте.

def show_main_menu(chat_id):
    from menu import main_menu
    # Используем stdlib SimpleNamespace для имитации объекта message с chat.id
    fake_message = SimpleNamespace(chat=SimpleNamespace(id=chat_id))
    main_menu(fake_message)


def handle_appointments_list_selection(message):
    """Обрабатывает выбор записи из списка; показывает детали выбранной записи."""
    chat_id = message.chat.id
    text = (message.text or "").strip()
    if text.lower() == 'назад':
        show_main_menu(chat_id)
        return
    # Ожидаем формат: "{date} {time} — {type} — {fio}". Найдём строку в базе по этим полям.
    try:
        parts = text.split('—')
        if len(parts) < 3:
            bot.send_message(chat_id, "Неверный выбор. Вернитесь и выберите запись снова.", reply_markup=types.ReplyKeyboardRemove())
            show_main_menu(chat_id)
            return
        left = parts[0].strip()  # date + time
        mtype = parts[1].strip()
        fio = '—'.join(parts[2:]).strip()
        try:
            date_part, time_part = left.split(' ', 1)
        except Exception:
            bot.send_message(chat_id, "Не удалось распознать дату/время. Попробуйте снова.")
            show_main_menu(chat_id)
            return

        from utils import excel_lock
        found_row = None
        with excel_lock:
            wb = openpyxl.load_workbook('db.xlsx')
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2):
                try:
                    if str(row[0].value) == str(chat_id):
                        r_date = str(row[4].value)
                        r_time = str(row[5].value)
                        r_type = str(row[3].value)
                        r_fio = str(row[1].value)
                        if r_date == date_part and r_time == time_part and r_type == mtype and r_fio == fio:
                            found_row = row[0].row
                            break
                except Exception:
                    continue
            wb.close()
        if not found_row:
            bot.send_message(chat_id, "Не удалось найти запись. Возможно, она уже отменена или изменена.")
            show_main_menu(chat_id)
            return
        show_appointment_details(chat_id, found_row)
    except Exception:
        logger.exception("Ошибка при обработке выбора записи")
        bot.send_message(chat_id, "Произошла ошибка. Попробуйте снова.")
        show_main_menu(chat_id)


def show_appointment_details(chat_id, row_num):
    """Показывает полную информацию о записи и клавиатуру для действий."""
    try:
        from utils import excel_lock
        with excel_lock:
            wb = openpyxl.load_workbook('db.xlsx')
            sheet = wb.active
            fio = sheet.cell(row=row_num, column=2).value
            phone = sheet.cell(row=row_num, column=3).value
            mtype = sheet.cell(row=row_num, column=4).value
            date_val = sheet.cell(row=row_num, column=5).value
            time_val = sheet.cell(row=row_num, column=6).value
            wb.close()
    except Exception as e:
        logger.error(f"Ошибка при получении деталей записи row={row_num}: {e}")
        bot.send_message(chat_id, "Ошибка при получении деталей записи. Попробуйте позже.")
        return

    text = (
        f"Запись #{row_num}:\n"
        f"ФИО: {fio}\n"
        f"Телефон: {phone}\n"
        f"Тип массажа: {mtype}\n"
        f"Дата: {date_val}\n"
        f"Время: {time_val}\n"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Перенести запись", "Отменить запись")
    markup.add("Назад")
    bot.send_message(chat_id, text, reply_markup=markup)
    # Регистрируем обработчик с передачей номера строки
    bot.register_next_step_handler_by_chat_id(chat_id, handle_appointment_action, row_num)


def handle_appointment_action(message, row_num):
    """Обрабатывает действия для выбранной записи (перенос/отмена/назад)."""
    chat_id = message.chat.id
    text = (message.text or "").strip().lower()
    if text == 'назад':
        # Показать список записей заново
        show_actions(message)
        return
    if text == 'отменить запись':
        # отмена конкретной строки
        if cancel_appointment_by_row(row_num):
            bot.send_message(chat_id, "Запись отменена.")
        else:
            bot.send_message(chat_id, "Не удалось отменить запись. Попробуйте позже.")
        show_main_menu(chat_id)
        return
    if text == 'перенести запись':
        try:
            from utils import excel_lock
            with excel_lock:
                wb = openpyxl.load_workbook('db.xlsx')
                sheet = wb.active
                fio = sheet.cell(row=row_num, column=2).value
                phone = sheet.cell(row=row_num, column=3).value
                mtype = sheet.cell(row=row_num, column=4).value
                old_date = sheet.cell(row=row_num, column=5).value
                old_time = sheet.cell(row=row_num, column=6).value
                wb.close()
        except Exception as e:
            logger.error(f"Ошибка при подготовке переноса для row={row_num}: {e}")
            bot.send_message(chat_id, "Не удалось подготовить перенос. Попробуйте позже.")
            return

        def make_reschedule_handler(rnum):
            def handler(message, fio_arg, phone_arg, mtype_arg, date_chosen, old_date_arg=None, old_time_arg=None):
                return reschedule_appointment_by_row(message, rnum, fio_arg, phone_arg, mtype_arg, date_chosen, old_date_arg, old_time_arg)
            return handler

        ask_date(message, fio or "Пациент", phone or "", mtype or "", make_reschedule_handler(row_num), old_date, old_time)
        return
    bot.send_message(chat_id, "Не понимаю команду. Вернитесь в меню.")
    show_main_menu(chat_id)


def cancel_appointment_by_row(row_num):
    try:
        from utils import excel_lock
        with excel_lock:
            wb = openpyxl.load_workbook("db.xlsx")
            sheet = wb.active
            # прочитаем данные для уведомления
            chat_cell = sheet.cell(row=row_num, column=1).value
            fio = sheet.cell(row=row_num, column=2).value
            phone = sheet.cell(row=row_num, column=3).value
            old_date = sheet.cell(row=row_num, column=5).value
            old_time = sheet.cell(row=row_num, column=6).value
            # отменим таймер, если он есть
            try:
                cancel_timer_by_row(row_num)
            except Exception:
                logger.exception(f"Не удалось отменить таймер для row={row_num} при cancel_by_row")
            sheet.delete_rows(row_num, 1)
            wb.save("db.xlsx")
            wb.close()
            logger.info(f"Удалена запись row={row_num}")
            try:
                notify_doctor_cancellation(chat_cell, old_date, old_time, fio=fio, phone_number=phone)
            except Exception:
                logger.exception("notify_doctor_cancellation failed in cancel_appointment_by_row")
            return True
    except Exception as e:
        logger.exception(f"Ошибка при cancel_appointment_by_row row={row_num}: {e}")
        return False


def update_appointment_by_row(row_num, new_date, new_time):
    try:
        from utils import excel_lock
        with excel_lock:
            wb = openpyxl.load_workbook("db.xlsx")
            sheet = wb.active
            chat_cell = sheet.cell(row=row_num, column=1).value
            old_date = sheet.cell(row=row_num, column=5).value
            old_time = sheet.cell(row=row_num, column=6).value
            try:
                remind_before = int(sheet.cell(row=row_num, column=7).value) if sheet.cell(row=row_num, column=7).value is not None else 180
            except Exception:
                remind_before = 180
            fio = sheet.cell(row=row_num, column=2).value
            # отменим старый таймер перед обновлением
            try:
                cancel_timer_by_row(row_num)
            except Exception:
                logger.exception(f"Не удалось отменить таймер для row={row_num} перед update_by_row")
            sheet.cell(row=row_num, column=5).value = new_date
            sheet.cell(row=row_num, column=6).value = new_time
            wb.save("db.xlsx")
            wb.close()
            logger.info(f"Обновление выполнено по row={row_num}: {old_date} {old_time} -> {new_date} {new_time} (remind_before={remind_before})")
            try:
                schedule_reminder(chat_cell, fio, new_date, new_time, remind_before)
            except Exception:
                logger.exception("Не удалось перепланировать напоминание после update_appointment_by_row")
            return True
    except Exception as e:
        logger.exception(f"Ошибка при update_appointment_by_row row={row_num}: {e}")
        return False


def reschedule_appointment_by_row(message, row_num, fio, phone_number, massage_type, new_date, old_date=None, old_time=None):
    """Ресайкл для обновления конкретной строки в БД после выбора времени"""
    chat_id = message.chat.id
    new_time = (message.text or "").strip()
    try:
        logger.info(f"Попытка перенести запись row={row_num} chat_id={chat_id} {old_date} {old_time} -> {new_date} {new_time}")
        ok = update_appointment_by_row(row_num, new_date, new_time)
        if ok:
            try:
                notify_doctor_reschedule(chat_id, fio, old_date, old_time, new_date, new_time)
            except Exception:
                logger.exception("notify_doctor_reschedule failed")
            bot.send_message(chat_id, "Ваша запись перенесена.")
        else:
            bot.send_message(chat_id, "Не удалось перенести запись. Попробуйте ещё раз.")
    except Exception as e:
        logger.exception(f"Ошибка при переносе записи по row={row_num}: {e}")
        bot.send_message(chat_id, "Произошла ошибка при переносе.")
    show_main_menu(chat_id)