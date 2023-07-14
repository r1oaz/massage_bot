import  telebot
from keyboards import main_menu_markup
from config import bot
def main_menu(message):
    bot.send_message(message.chat.id, "Выберите пункт из меню:", reply_markup=main_menu_markup())
