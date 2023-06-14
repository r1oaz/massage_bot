import telebot
from bot import bot
def main_menu(message):
	keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
	keyboard.add("Записаться на массаж", "Посмотреть прайс", "Проверить свободное время")
	bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)