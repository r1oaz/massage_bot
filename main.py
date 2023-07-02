import telebot
from reg_mas import register_massage
from show_price import show_pricelist
from menu import main_menu
from check_time import check_availability
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
# запуск бота
	print('starting...')
	try:
		bot.polling(none_stop=True, interval=0)
		#print('Этого не должно быть')
		exit()
		# если досюда дошёл бот, это совершенно нормально. Мы нажали ctrl+c!
		with open("exit.log", "w", encoding="UTF-8") as f: f.write("exited!")
	except KeyboardInterrupt:
			exit() # ctrl+c pressed
	except telebot.apihelper.ApiException:
		print('Проверьте связь и API')
		sleep(10)
	except Exception as e:
		print(e)
		sleep(15)

if __name__ == '__main__':
	run_bot()
