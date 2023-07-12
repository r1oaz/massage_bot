from telebot import types
import openpyxl

# загрузка прайс-листа
book = openpyxl.load_workbook("price.xlsx")
sheet = book.active

def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("Прайс"),
        types.KeyboardButton("Записаться"),
        types.KeyboardButton("Проверить свободное время")
    )
    return markup

def massage_types_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in sheet.iter_rows(min_row=2, max_col=1):
        markup.add(row[0].value)
    return markup

def time_slots_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("09:00"),
        types.KeyboardButton("09:30"),
        types.KeyboardButton("10:00"),
        types.KeyboardButton("10:30"),
        types.KeyboardButton("11:00"),
        types.KeyboardButton("11:30"),
        types.KeyboardButton("12:00"),
        types.KeyboardButton("13:00"),
        types.KeyboardButton("13:30"),
        types.KeyboardButton("14:00"),
        types.KeyboardButton("14:30"),
        types.KeyboardButton("15:00"),
        types.KeyboardButton("15:30"),
        types.KeyboardButton("16:00"),
        types.KeyboardButton("16:30")
    )
    return markup
