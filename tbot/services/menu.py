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

from tbot.services.executors import Executor, ExeAddBusStop
from tbot.services.functions import authorize


def menu(bot, message, open_menu=None):
    """Принимает объект бота и сообщение пользователя полученное из телеграмм.
    Третий аргумент, если есть - это меню, которое нужно отобразить."""

    # Определение пользовательских клавиатур
    kb = dict()

    # Настройки
    settings_menu = {
        'Настройки': [
            {'Добавить остановку': ExeAddBusStop, 'Редактировать маршрут': Executor},
            {'Назад': 'Дополнительно'}
        ]
    }

    # Полное расписание
    full_shedule_menu = {
        'Полное расписание': [
            {'С остановки': Executor, 'По маршруту': Executor},
            {'Назад': 'Дополнительно'}
        ]
    }

    # Дополнительно
    add_menu = {
        'Дополнительно': [
            {'Настройки': 'Настройки', 'Полное расписание': 'Полное расписание'},
            {'Назад': 'Главное меню'}
        ]
    }

    # Главное меню
    main_menu = {
        'Главное меню': [
            {'Мои маршруты': Executor, 'Дополнительно': 'Дополнительно'},
        ]
    }

    # Объединить все меню в один словарь
    kb.update(main_menu)
    kb.update(add_menu)
    kb.update(settings_menu)
    kb.update(full_shedule_menu)

    # Проверка и авторизация пользователя
    user = authorize(message)
    if not user:
        # Для ботов
        raise PermissionDenied

    if not open_menu:
        # Если второй параметр - объект, то это сообщение пользователя
        # Ищем в текущем меню слово из сообщения (нажатую кнопку)
        point_menu = None
        for item in kb[user.user_menu]:
            if message.text in item:
                # Найдена нажатая кнопка меню (клавиатуры)
                point_menu = item[message.text]
                break
    else:
        # Если второй параметр - строка, то это просто меню которое нужно отобразить
        point_menu = open_menu

    # Для перехода к другому меню (клавиатуре) в найденном результате будет str
    # Если там не строка - значит это действие в окне чата или что-то другое.
    if isinstance(point_menu, str):
        # Запоминаем новое меню пользователя
        user.user_menu = point_menu
        user.save()

        # В списке количество словарей - это количество строк,
        # а количество ключей в словаре - это количество кнопок в строке.
        # Отображаем клавиатуру соответствующего вида
        markup = types.ReplyKeyboardMarkup()
        for item in kb[point_menu]:
            markup.row(*(types.KeyboardButton(button) for button in item.keys()))
        bot.send_message(message.chat.id, f'{point_menu}', reply_markup=markup)

        return

    # Если в point_menu класс ExeAddBusStop, то это действие в окне чата
    if point_menu == ExeAddBusStop:
        point_menu(bot, user, None)
        return

    bot.send_message(message.chat.id, f"{message.text}")

