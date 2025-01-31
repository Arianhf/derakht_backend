import jdatetime
from django import template

register = template.Library()


@register.filter(name='jalali_format')
def jalali_format(value, format_string=None):
    if not value:
        return ''
    if isinstance(value, jdatetime.datetime) or isinstance(value, jdatetime.date):
        jalali_date = value
    else:
        jalali_date = jdatetime.date.fromgregorian(date=value)

    if format_string:
        return jalali_date.strftime(format_string)

    # Default format if none specified
    return jalali_date.strftime('%Y/%m/%d')


@register.filter(name='jalali_monthname')
def jalali_monthname(value):
    if not value:
        return ''
    if not isinstance(value, jdatetime.date):
        value = jdatetime.date.fromgregorian(date=value)

    months = {
        1: 'فروردین',
        2: 'اردیبهشت',
        3: 'خرداد',
        4: 'تیر',
        5: 'مرداد',
        6: 'شهریور',
        7: 'مهر',
        8: 'آبان',
        9: 'آذر',
        10: 'دی',
        11: 'بهمن',
        12: 'اسفند'
    }
    return months.get(value.month, '')


@register.filter(name='jalali_weekday')
def jalali_weekday(value):
    if not value:
        return ''
    if not isinstance(value, jdatetime.date):
        value = jdatetime.date.fromgregorian(date=value)

    weekdays = {
        2: 'دوشنبه',
        3: 'سه‌شنبه',
        4: 'چهارشنبه',
        5: 'پنج‌شنبه',
        6: 'جمعه',
        0: 'شنبه',
        1: 'یکشنبه'
    }
    return weekdays.get(value.weekday(), '')


@register.simple_tag
def full_jalali_date(value):
    if not value:
        return ''
    if not isinstance(value, jdatetime.date):
        value = jdatetime.date.fromgregorian(date=value)

    weekday = jalali_weekday(value)
    day = value.strftime('%d')
    month = jalali_monthname(value)
    year = value.strftime('%Y')

    return f"{weekday} {day} {month} {year}"
