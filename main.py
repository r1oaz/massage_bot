import telebot
from reg_mas import register_massage
from show_price import show_pricelist
from menu import main_menu
from check_time import check_availability
from bot import bot
# инициализация бота
def run_bot():
	# обработка команды /start
	@bot.message_handler(commands=["start"])
	def start(message):
# главное меню
		main_menu(message)
# обработка выбора "записаться на массаж"
	@bot.message_handler(func=lambda message: message.text == "Записаться на массаж")
	def reg(message):
		print('старт запись на массаж')
		register_massage(message)
# обработка выбора "посмотреть прайс"
	@bot.message_handler(func=lambda message: message.text == "Посмотреть прайс")
	def show_price(message):
		print('старт показать прайс')
		show_pricelist(message)
# обработка выбора "проверить свободное время"
	@bot.message_handler(func=lambda message: message.text == "Проверить свободное время")
	def check_times(message):
		print('старт проверить время')
		check_availability(message)