
from telebot import types
import openpyxl

def main_menu_markup():
    """Главное меню"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("Прайс"),
        types.KeyboardButton("Записаться"),
    )
    return markup

def massage_types_markup():
    """Клавиатура с типами массажа из price.xlsx"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    try:
        book = openpyxl.load_workbook("price.xlsx")
        sheet = book.active
        for row in sheet.iter_rows(min_row=2, max_col=1):
            if row[0].value:
                markup.add(str(row[0].value))
        book.close()
    except Exception:
        markup.add("Ошибка загрузки типов массажа")
    return markup

