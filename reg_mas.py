import telebot
import openpyxl
from keyboards import massage_types, yes_no_keyboard, times_keyboard
def register_massage(message):
	bot.send_message(message.chat.id, "Введите ФИО:")
	bot.register_next_step_handler(message, get_name)
# получение ФИО
def get_name(message):
	name = message.text
	bot.send_message(message.chat.id, "Введите номер телефона:")
	bot.register_next_step_handler(message, get_phone, name)
# получение номера телефона
def get_phone(message, name):
	phone = message.text
	bot.send_message(message.chat.id, "Выберите вид массажа:", reply_markup=massage_types)
	bot.register_next_step_handler(message, get_massage_type, name, phone)
# получение вида массажа
def get_massage_type(message, name, phone):
	massage_type = message.text
	bot.send_message(message.chat.id, "Есть ли у вас направление на массаж?", reply_markup=yes_no_keyboard)
	bot.register_next_step_handler(message, get_direction, name, phone, massage_type)
# получение направления на массаж
def get_direction(message, name, phone, massage_type):
	direction = message.text
	bot.send_message(message.chat.id, "Введите дату	 (в формате ДД.ММ.ГГГГ):")
	bot.register_next_step_handler(message, get_date, name, phone, massage_type, direction)
def get_date(message, name, phone, massage_type, direction):
	date = message.text
	bot.send_message(message.chat.id, "выбирите время:", reply_markup=times_keyboard)
	bot.register_next_step_handler(message, get_time, name, phone, massage_type, direction, date)
def get_time(message, name, phone, massage_type, direction, date):
	time = message.text
	print("wow! got time!")
	# мы сохранили время. Сразу спрашиваем подтверждение без ожидания сообщения!
	response = f"Вас зовут {name}, вы записались на массаж {massage_type}, ваш телефон {phone}, направление на массаж {direction}, дата и время {date} {time}. всё-ли верно?"
	bot.send_message(message.chat.id, response, reply_markup=yes_no_keyboard)
	bot.register_next_step_handler(message, save_registration, name, phone, massage_type, direction, date, time)
# сохранение записи на массаж
def save_registration(message, name, phone, massage_type, direction, date, time):
	if message.text == "Да":
# Открытие файла с записями
		wb = openpyxl.load_workbook('mas.xlsx')
		sheet = wb.active
		sheet.append([name, phone, massage_type, direction, date, time])
		wb.save("mas.xlsx")
		bot.send_message(doktor_id, f"{name} записался на массаж {massage_type} на {date} в {time} телефон: {phone}")
		bot.send_message(message.chat.id, "Запись сохранена")
		main_menu(message)
	else:
			register_massage(message)