from telebot import types
from keyboards import main_menu_markup
from config import bot
def main_menu_message(chat_id):
    bot.send_message(chat_id, "Выберите пункт из меню:", reply_markup=main_menu_markup())
