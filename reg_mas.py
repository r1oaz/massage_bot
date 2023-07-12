import openpyxl
from telebot import types
from keyboards import massage_types_markup, time_slots_markup
from menu import main_menu_markup
import datetime
from config import bot, doktor_id
def register_massage(message):
    # Запрашиваем данные от пользователя
    bot.send_message(message.chat.id, "Введите ФИО:")
    bot.register_next_step_handler(message, ask_phone_number)

def ask_phone_number(message):
    # Сохраняем ФИО и запрашиваем номер телефона
    fio = message.text
    bot.send_message(message.chat.id, "Введите номер телефона:")
    bot.register_next_step_handler(message, ask_massage_type, fio)

def ask_massage_type(message, fio):
    # Сохраняем номер телефона и предлагаем выбрать тип массажа
    phone_number = message.text
    bot.send_message(message.chat.id, "Выберите тип массажа:", reply_markup=massage_types_markup())
    bot.register_next_step_handler(message, ask_date, fio, phone_number)

def ask_date(message, fio, phone_number):
    # Сохраняем тип массажа и предлагаем ввести дату
    massage_type = message.text
    bot.send_message(message.chat.id, "Введите дату (в формате дд.мм.гггг):")
    bot.register_next_step_handler(message, ask_time, fio, phone_number, massage_type)

def ask_time(message, fio, phone_number, massage_type):
    # Проверяем введенную дату на корректность и предлагаем выбрать время
    date = message.text
    if check_date_format(date):
        bot.send_message(message.chat.id, "Выберите время:", reply_markup=time_slots_markup())
        bot.register_next_step_handler(message, confirm_registration, fio, phone_number, massage_type, date)
    else:
        bot.send_message(message.chat.id, "Некорректный формат даты. Введите дату (в формате дд.мм.гггг):")
        bot.register_next_step_handler(message, ask_time, fio, phone_number, massage_type)

def confirm_registration(message, fio, phone_number, massage_type, date):
    # Подтверждаем запись и сохраняем данные в файл db.xlsx
    time_slot = message.text
    bot.send_message(message.chat.id, "Подтвердите запись:\n\n"
                                      f"ФИО: {fio}\n"
                                      f"Номер телефона: {phone_number}\n"
                                      f"Тип массажа: {massage_type}\n"
                                      f"Дата: {date}\n"
                                      f"Время: {time_slot}",
                     reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("Да"),
                                                                                        types.KeyboardButton("Нет")))
    bot.register_next_step_handler(message, save_registration, fio, phone_number, massage_type, date, time_slot)

def save_registration(message, fio, phone_number, massage_type, date, time_slot):
    # Сохраняем данные о записи в файл db.xlsx
    if message.text.lower() == 'да':
        wb = openpyxl.load_workbook('db.xlsx')
        sheet = wb.active
        row = [fio, phone_number, massage_type, date, time_slot]
        sheet.append(row)
        wb.save('db.xlsx')
        bot.send_message(doktor_id, 'записался на массаж:', row)
        bot.send_message(message.chat.id, "Ваша запись сохранена. Ждем вас на массаж!", reply_markup=main_menu_markup())
    else:
        register_massage(bot, message)

def check_date_format(date):
    # Проверяем корректность формата даты
    try:
        datetime.datetime.strptime(date, '%d.%m.%Y')
        return True
    except ValueError:
        return False
