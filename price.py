import openpyxl
from config import bot
from menu import main_menu
def show_price(message):
    wb = openpyxl.load_workbook('price.xlsx')
    sheet = wb.active
    prices = []

    for row in sheet.iter_rows(values_only=True):
        prices.append(f"{row[0]}: {row[1]}")

    price_text = '\n'.join(prices)
    bot.send_message(message.chat.id, f"Прайс на массаж:\n{price_text}")
    main_menu(message)
