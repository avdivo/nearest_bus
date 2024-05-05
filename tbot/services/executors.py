# Классы для выполнения действий в окне чата.
# Изменение параметров, выбор опций...

import json
import random
import string
import telebot
import datetime
from telebot import types

from django.utils import timezone

from schedule.models import BusStop, Schedule


class Executor:
    """Базовый класс для выполнения действий в окне чата.
    Устанавливает общие аттрибуты для всех действий при начале,
    восстанавливает их при продолжениях, и имеет метод для сохранения.
    """
    def __init__(self, bot, user, bot_object, action=None):
        """
        """
        # Не сохраняемые параметры объекта
        self.user = user  # Пользователь
        self.bot_object = bot_object  # Оригинальный полученный объект, если понадобится программам
        self.bot = bot  # Бот

        if type(bot_object) == types.Message:
            # Параметры зависящие от типа объекта
            self.kb_id, self.key_name = None, None  # Идентификатор и название клавиши
            self.message = bot_object  # Объект сообщения
        else:
            self.kb_id, self.key_name = bot_object.data.split('_')
            self.message = bot_object.message  # Объект сообщения
        data = dict()
        if action is None:
            # Продолжение выполнения программы
            data = json.loads(user.parameter.addition)  # Получаем данные с которыми она работает из БД

        # Сохраняемые параметры объекта
        self.stage = data.get('stage', 0)  # Этап выполнения программы
        self.kb_wait = data.get('kb_id', [])  # ids клавиатур от которых ожидаем ответа
        self.other_fields = data.get('other_fields', dict())  # Дополнительные поля

        if not self.kb_id or self.kb_id in self.kb_wait:
            # Если id клавиатуры нет, то это начало программы или программа ожидает не клавиатуру.
            # Если id есть, он должен входить в список.
            # В этих случаях действие выполняется.

            # Получим название класса и запишем его в БД
            user.parameter.class_name = self.__class__.__name__
            user.parameter.save()
            self.execute()  # Выполняем действие

            self.save()  # Сохраняем параметры выполнения программы в БД

    def execute(self):
        """Выполняет действие. В классах - наследниках переопределяется."""
        pass

    def save(self):
        """Сохраняет параметры действия в БД."""
        data = {
            'stage': self.stage,
            'kb_id': self.kb_wait,
            'other_fields': self.other_fields
        }
        self.user.parameter.addition = json.dumps(data, ensure_ascii=False)
        self.user.parameter.save()

    def keyboard(self, message: str, names: (list, dict), row=1, replace=False):
        """Создает InlineKeyboardMarkup клавиатуру из заданного списка.
        Может вывести клавиатуру с отметками выбранных клавиш (галочка перед названием),
        для этого в качестве списка должен быть передан словарь: {name: True/False}.
        Если replace=True, заменяет клавиатуру в чате.
        Принимает: сообщение (название клавиатуры), список названий клавиш,
        количество клавиш в строке и флаг замены клавиатуры.
        Возвращает: идентификатор клавиатуры. Он фигурирует в названии клавиш: идентификатор_название.
        Выводит клавиатуру в чат.
        """
        # Генерируем уникальный id для клавиатуры
        characters = string.ascii_letters + string.digits
        kd_id = ''.join(random.choice(characters) for _ in range(6))

        # Готовим словарь названий клавиш, даже если был передан список
        if isinstance(names, dict):
            name_dict = names
        else:
            name_dict = {name: False for name in names}

        # Подготовка клавиатуры
        keyboard = types.InlineKeyboardMarkup()
        buttons = []
        for name, selected in name_dict.items():
            sel = '✓ ' if selected else ''
            button = types.InlineKeyboardButton(text=sel+name, callback_data=f'{kd_id}_{name}')
            buttons.append(button)

        # Добавляем кнопки в разметку заданное количество раз в строке
        for i in range(0, len(buttons), row):
            keyboard.add(*buttons[i:i+row])

        if replace:
            self.bot.edit_message_text(chat_id=self.message.chat.id, message_id=self.message.message_id,
                                       text=message, reply_markup=keyboard)
        else:
            self.bot.send_message(self.message.chat.id, message, reply_markup=keyboard)

        return kd_id


class ExeAddBusStop(Executor):
    """Добавление остановки в Мои маршруты."""

    def execute(self):
        """Добавляет остановку в избранное."""
        if self.stage == 0:
            # ---------------- 1 этап - запрос остановки ----------------
            # Составим список остановок без повторений, в алфавитном порядке
            stops = set()
            for stop in BusStop.objects.all():
                stops.add(stop.name)
            stops = sorted(list(stops))

            # Отправляем сообщение с клавиатурой и запоминаем ее id
            self.kb_wait = [self.keyboard('Выберите остановку отправления:', stops, row=2)]

        if self.stage == 1:
            # ---------------- 2 этап - запрос направления ----------------
            # Находим остановку по названию
            bus_stop = BusStop.objects.filter(name=self.key_name)
            for_kb = set()
            for stop in bus_stop:  # Остановка с 1 названием может быть 2 (в разных направлениях)
                related_stops = stop.get_related_stops()  # Получаем связанные остановки
                for_kb.update([one.name for one in related_stops])  # Добавляем в множество их названия
            for_kb = sorted(list(for_kb))

            # Отправляем сообщение с клавиатурой
            self.kb_wait = [self.keyboard('Выберите остановку назначения:', for_kb, row=2)]
            self.other_fields['start'] = self.key_name  # Сохраняем начальную остановку

        if self.stage == 2:
            # ---------------- 3 этап - запрос имени для сохранения ----------------
            # Находим объекты остановок по названиям и направлению
            bs_dict = BusStop.get_routers_by_two_busstop(self.other_fields['start'], self.key_name)
            try:
                # Сохраняем id начальной остановки
                self.other_fields['start'] = bs_dict['start'].external_id
                # Список автобусов на остановке
                buses = bs_dict['start'].get_bus_by_stop()
            except AttributeError:
                # Если остановка не найдена, то выводим сообщение и завершаем действие
                self.bot.send_message(self.message.chat.id, 'Возможно между этими остановками нет прямого маршрута. '
                                                            'Попробуйте выбрать другие остановки.')
                self.stage = 0
                return

            # Составляем строку для сообщения
            string = (f'На остановке "{bs_dict["start"].name}"\nостанавливаются следующие автобусы:\n' +
                      ', '.join([str(bus.number) for bus in buses]) +
                      f'.\n\nИз них, по выбранному вами маршруту, до остановки "{self.key_name}" идут автобусы:\n' +
                      ', '.join([str(bus.number) for bus in bs_dict['buses']]) +
                      '.\n\nВведите имя для сохранения в Мои маршруты. После сохранения вы сможете откорректировать маршрут.')

            # Отправляем сообщение со списком автобусов и приглашением ввести имя для сохранения
            self.bot.send_message(self.message.chat.id, string)

            # Сохраняем параметры
            self.other_fields['finish'] = bs_dict['finish'].external_id
            self.other_fields['check'] = [bus.number for bus in bs_dict['buses']]  # Список автобусов которые будут сохранены как выбранные
            self.kb_wait.clear()

        if self.stage == 3:
            # ---------------- 4 этап - сохранение ----------------
            # Должно прийти имя для сохранения, сохраняем новый маршрут с этим именем
            name = self.message.text
            if not name:
                name = f'Маршрут {self.other_fields["start"]} - {self.other_fields["finish"]}'

            # Сохраняем маршрут в Избранное (favorites)
            save = json.loads(self.user.parameter.favorites)
            save[name] = {'start': self.other_fields['start'], 'finish': self.other_fields['finish'],
                         'check': self.other_fields['check']}
            self.user.parameter.favorites = json.dumps(save, ensure_ascii=False)
            self.user.parameter.save()

            # Отправляем сообщение об успешном сохранении
            self.bot.send_message(self.message.chat.id, f'Маршрут "{name}" сохранен в Мои маршруты.')

        self.stage += 1


class MyRouter(Executor):
    """Выводит список сохраненных маршрутов.
    Предоставляет выбор маршрута.
    Отображает расписание на начальной остановке маршрута."""

    def execute(self):
        """Показывает короткое расписание автобусов на выбранном маршруте."""
        if self.stage == 0:
            # ---------------- 1 этап - запрос маршрута ----------------
            # Выводим список маршрутов их Избранного
            favorites = json.loads(self.user.parameter.favorites)
            self.kb_wait = [self.keyboard('Выберите маршрут:', favorites.keys(), row=1)]

        if self.stage == 1:
            # ---------------- 2 этап - вывод расписания ----------------
            # Получаем данные о маршруте
            favorites = json.loads(self.user.parameter.favorites)
            start = favorites[self.key_name]['start']
            check = favorites[self.key_name]['check']

            # Находим объект остановки по id
            start = BusStop.objects.get(external_id=start)

            # Определяем текущее время с поправкой на часовой пояс
            current_timezone = timezone.get_current_timezone()
            utc_time = timezone.now()  # получаем текущее время в UTC
            now = utc_time.astimezone(current_timezone).time()  # конвертируем время в текущий часовой пояс

            # Создать переменную с временем 15:21
            now = datetime.time(15, 21)

            # Текущий день недели (1-7)
            day = datetime.datetime.now().isoweekday()

            # Для каждого автобуса в списке из favorites.
            # Найдем в модели Schedule 2 записи с этим автобусом и остановкой start после текущего времени.
            # Отсортируем по времени и сохраним в словарь по автобусу.
            schedule = dict()
            for bus in check:
                # Находим записи в расписании
                sch = Schedule.objects.filter(bus_stop=start, bus__number=bus, time__gte=now, day=day).order_by('time')
                time_strings = [time_obj.strftime('%H:%M') for time_obj in sch.values_list('time', flat=True)]
                schedule[bus] = time_strings  # Сохраняем в словарь

            # Составляем строку для сообщения
            string = f'{self.key_name}\n"{start.name}"\n'
            for bus, times in schedule.items():
                times = times[:2]  # Выводим только первые 2 времени
                if times:
                    string += f'Автобус {bus}: {",  ".join(times)}\n\n'

            # Отправляем расписание
            self.bot.send_message(self.message.chat.id, string)

        self.stage += 1