import  telebot
from keyboards import main_menu_markup
from config import bot
def main_menu(message):
    """Показывает главное меню пользователю"""
    bot.send_message(message.chat.id, "Выберите пункт из меню:", reply_markup=main_menu_markup(message.chat.id))
