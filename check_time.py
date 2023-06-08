import telebot
import openpyxl
from menu import main_menu
from main import bot
def check_availability(message):
	print('проверка свободного времени')
	bot.send_message(message.chat.id, "Введите дату (в формате ДД.ММ.ГГГГ):")
	bot.register_next_step_handler(message, check_available_time)
# функция для проверки доступного времени на определенную дату
	def check_available_time(message):
		date = message.text
		print(date)
#загрузка файла Excel с расписанием массажа
		workbook = openpyxl.load_workbook('mas.xlsx')
		worksheet = workbook.active
# список доступных времен
		available_times = ["9:30", "10:00", "10:30", "11:00", "11:30", "12:00", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"]
## список занятых времен на заданную дату
		busy_times = []
# проходим по всем строкам в таблице
		for row in worksheet.iter_rows(min_row=2, values_only=True):
# если дата в текущей строке совпадает с заданной датой
			if row[5] == date:
			# добавляем занятое время в список
				busy_times.append(row[6])
# удаляем занятые времена из списка доступных времен
		for busy_time in busy_times:
			if busy_time in available_times:
				available_times.remove(busy_time)
		# отправляем сообщение с доступными временами
				bot.send_message(message.chat.id, f"Доступное время на {date}: {available_times}")
				print("Доступное время на {date}: {available_times}")
			else:
				print('на', date,' всё свободно')
				bot.send_message(message.chat.id, f"На {date} всё свободно")
		main_menu(message)