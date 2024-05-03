# Классы для выполнения действий в окне чата.
# Изменение параметров, выбор опций...

import json
import telebot
from telebot import types

from schedule.models import BusStop


class Executor:
    """Базовый класс для выполнения действий в окне чата.
    Устанавливает общие аттрибуты для всех действий при начале,
    восстанавливает их при продолжениях, и имеет метод для сохранения.
    """
    def __init__(self, bot, user, call):
        """Определяет начало действий по наличию объекта call.
        Если его нет устанавливает начальные аттрибуты.
        Если есть, определяет по id сообщения ждет ли его класс исполнитель."""
        # Устанавливаем начальные аттрибуты
        data = dict()
        if call:
            # Если есть call, то это продолжение действия или начало нового
            data = json.loads(user.parameter.addition)
        self.user = user  # Пользователь
        self.bot = bot  # Бот
        self.stage = data.get('stage', 0)  # Этап выполнения программы
        self.message_id = data.get('message_id', [])  # ids сообщения от которых ожидаем ответа
        self.other_fields = data.get('other_fields', dict())  # Дополнительные поля

        if not call or call.message.message_id in self.message_id:
            # Выполняется действие если это начало или продолжение от ожидаемой клавиатуры
            self.execute()

    def execute(self):
        """Выполняет действие. В классах - наследниках переопределяется."""
        pass


class ExeAddBusStop(Executor):
    """Добавление остановки в Мои маршруты."""

    def execute(self):
        """Добавляет остановку в избранное."""
        # ---------------- 1 этап - запрос остановки ----------------
        # Составим список остановок без повторений, в алфавитном порядке
        stops = set()
        for stop in BusStop.objects.all():
            stops.add(stop.name)
        stops = sorted(list(stops))

        # Выводим клавиатуру InlineKeyboardMarkup с остановками в 2 ряда
        keyboard = types.InlineKeyboardMarkup()
        for i in range(0, len(stops), 2):
            try:
                button1 = types.InlineKeyboardButton(text=stops[i], callback_data=f'stop_{stops[i]}')
                button2 = types.InlineKeyboardButton(text=stops[i + 1], callback_data=f'stop_{stops[i + 1]}')
                keyboard.add(button1, button2)
            except IndexError:
                button = types.InlineKeyboardButton(text=stops[i], callback_data=f'stop_{stops[i]}')
                keyboard.add(button)


        # Отправляем сообщение с клавиатурой
        self.bot.send_message(self.user.user_id, 'Выберите остановку отправления:', reply_markup=keyboard)




