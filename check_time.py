import openpyxl
from telebot import types
from keyboards import main_menu_markup
from config import bot
def check_available_time(message):
    bot.send_message(message.chat.id, "Введите дату (в формате дд.мм.гггг):")
    bot.register_next_step_handler(message, show_available_time)

def show_available_time(message):
    date = message.text
    available_times = get_available_times(date)

    if available_times:
        bot.send_message(message.chat.id, f"Свободное время на {date}:\n\n{', '.join(available_times)}")
    else:
        bot.send_message(message.chat.id, "На данную дату нет свободного времени")

    bot.send_message(message.chat.id, "Выберите пункт из меню:", reply_markup=main_menu_markup())

def get_available_times(date):
    wb = openpyxl.load_workbook('db.xlsx')
    sheet = wb.active
    times = []

    for row in sheet.iter_rows(values_only=True):
        if row[3] == date:
            times.append(row[4])

    all_times = ['09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30']

    available_times = [time for time in all_times if time not in times]

    return available_times
