import telebot
from reg_mas import register_massage
from show_price import show_pricelist
from menu import main_menu
from check_time import check_availability
from config import Token
from time import sleep
# инициализация бота
def run_bot():
	bot = telebot.TeleBot(Token)
	print('starting...')
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
# запуск бота
	print('starting...')
	try:
		bot.polling(none_stop=True, interval=0)
		#print('Этого не должно быть')
	except telebot.apihelper.ApiException:
		print('Проверьте связь и API')
		sleep(10)
	except Exception as e:
		print(e)
		sleep(15)

if __name__ == '__main__':
	run_bot()
