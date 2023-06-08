import openpyxl
from main import bot
from menu import main_menu
def show_pricelist(message):
	print('показываем прайс')
	book = openpyxl.load_workbook("прайс.xlsx")
	sheet = book.active
	response = ""
	for row in sheet.iter_rows(min_row=2, max_col=2):
		response += f"{row[0].value} - {row[1].value}\n"
	bot.send_message(message.chat.id, response)
	main_menu(message)
