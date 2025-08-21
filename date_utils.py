import datetime

def is_valid_date(date_text):
    """Проверяет, что дата в формате ДД.ММ.ГГГГ и не в прошлом"""
    try:
        date_obj = datetime.datetime.strptime(date_text, '%d.%m.%Y').date()
        return date_obj >= datetime.date.today()
    except ValueError:
        return False

def is_weekend(date):
    """Проверяет, что дата - выходной (суббота или воскресенье)"""
    return date.weekday() >= 5

def check_date_format(date):
    """Проверяет только формат даты, не учитывая актуальность"""
    try:
        datetime.datetime.strptime(date, '%d.%m.%Y')
        return True
    except ValueError:
        return False
