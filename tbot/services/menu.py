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

from tbot.services.executors import Executor, ExeAddBusStop, MyRouter
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
            {'Мои маршруты': MyRouter, 'Дополнительно': 'Дополнительно'},
        ]
    }

    # Объединить все меню в один словарь
    kb.update(main_menu)
    kb.update(add_menu)
    kb.update(settings_menu)
    kb.update(full_shedule_menu)

    # Проверка и авторизация пользователя
    user = authorize(message.from_user)
    if not user:
        # Для ботов
        raise PermissionDenied

    if not open_menu:
        # Ищем в текущем меню слово из сообщения (нажатую кнопку)
        point_menu = None
        for item in kb[user.user_menu]:
            if message.text in item:
                # Найдена нажатая кнопка меню (клавиатуры)
                point_menu = item[message.text]
                break
    else:
        # Специально введено, чтобы отображать любое меню. Например, при старте
        point_menu = open_menu

    # Для перехода к другому меню (клавиатуре) в найденном результате будет str
    # Если там не строка - значит это действие в окне чата или что-то другое.
    # Если там None - значит кнопка не найдена, возможно просто введен текст.
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

    # Мы пришли сюда если в point_menu пусто или там имя класса новой программы.
    if point_menu:
        # Если в point_menu класс, то это начало программы в окне чата
        point_menu(bot, user, message, action=True)
        return

    # Если в point_menu пусто, то в message.text текст сообщения от пользователя,
    # он может быть нужен программе в окне чата, передаем его.
    # Если в ответ получим None, значит программе он не нужен.
    if user.parameter.class_name:
        # В переменной class_name хранится название класса программы,
        # которая выполняется для этого пользователя, создаем объект,
        # одновременно запустится продолжение выполнения программы.
        answer = globals()[user.parameter.class_name](bot, user, message)

        # Тут можно обработать необработанные сообщения, если answer is None.

    else:
        # Если нет программы, сообщаем об ошибке, такого быть не должно
        print(f"Произошла ошибка:")
        bot.send_message(message.chat.id, "Запрос не обработан.")




