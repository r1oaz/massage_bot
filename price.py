import openpyxl
from config import bot
from menu import main_menu

def show_price(message):
    """Показывает прайс-лист на массаж"""
    try:
        wb = openpyxl.load_workbook('price.xlsx')
        sheet = wb.active
        prices = []
        for row in sheet.iter_rows(values_only=True):
            if row[0] and row[1]:
                prices.append(f"{row[0]}: {row[1]}")
        wb.close()
        if prices:
            price_text = '\n'.join(prices)
            bot.send_message(message.chat.id, f"Прайс на массаж:\n{price_text}")
        else:
            bot.send_message(message.chat.id, "Прайс-лист пуст или не заполнен.")
    except FileNotFoundError:
        bot.send_message(message.chat.id, "Ошибка: файл с прайс-листом не найден.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")
    main_menu(message)
