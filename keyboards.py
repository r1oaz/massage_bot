import telebot
import openpyxl
# загрузка прайс-листа
book = openpyxl.load_workbook("прайс.xlsx")
sheet = book.active
# клавиатуры
massage_types = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
for row in sheet.iter_rows(min_row=2, max_col=1):
	massage_types.add(row[0].value)
yes_no_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
yes_no_keyboard.add("Да", "Нет")
times_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
times_keyboard.add("9:30", "10:00", "10:30", "11:00", "11:30", "12:00", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30")