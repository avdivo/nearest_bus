# Модуль отвечающий за отображение и перемещению по Меню.
# Меню - это пользовательская клавиатура.
# Осуществляет запуск программ.

# Читает текущее состояние из свойств пользователя.
# По нему определяет в каком месте меню находится
# и получает параметры для запуска программ -
# восстанавливает объект Исполнителя и запуск его метода.

from django.core.exceptions import PermissionDenied

from tbot.models import BotUser

from telebot import types

from tbot.services.executors import Executor
from tbot.services.functions import authorize


def menu(bot, message):
    """Принимает объект бота и сообщение пользователя полученное из телеграмм.
    """
    text = message.text

    # Определение пользовательских клавиатур
    kb = dict()
    kb['Дополнительно'] = None
    kb['Главное меню'] = None

    # Настройки
    kb['Настройки'] = [
        {'Добавить остановку': Executor, 'Редактировать маршрут': Executor},
        {'Назад': 'Дополнительно'}
    ]

    # Полное расписание
    kb['Полное расписание'] = [
        {'С остановки': Executor, 'По маршруту': Executor},
        {'Назад': 'Дополнительно'}
    ]

    # Дополнительно
    kb['Дополнительно'] = [
        {'Настройки': kb['Настройки'], 'Полное расписание': kb['Полное расписание']},
        {'Назад': 'Главное меню'}
    ]

    # Главное меню
    kb['Главное меню'] = [
        {'Мои маршруты': Executor, 'Дополнительно': kb['Дополнительно']},
    ]

    user = authorize(message)
    if not user:
        raise PermissionDenied

    menu_items = dict()
    back_menu = None
    for item in kb[user.user_menu]:
        for key in item.keys():
            menu_items[key] = item[key]
            if key == 'Назад':
                back_menu = item[key]

    if text in menu_items:
        # Нажата кнопки входящая в меню
        if isinstance(kb[text], (list, str)):
            # Если в этом пункте меню список или строка - то это другое меню.
            # Проверим на кнопку Назад и обработаем отдельно
            if text == 'Назад':
                text = menu_items[back_menu]

            # В списке количество словарей - это количество строк,
            # а количество ключей в словаре - это количество кнопок в строке.
            # Отображаем клавиатуру соответствующего вида
            markup = types.ReplyKeyboardMarkup()
            for item in kb[text]:
                markup.row(*(types.KeyboardButton(button) for button in item.keys()))
            bot.send_message(message.chat.id, 'Выберите:', reply_markup=markup)

            # Запоминаем текущее меню пользователя
            user.user_menu = text
            user.save()
        return

    bot.send_message(message.chat.id, "Ничего не выбрано.")