# Классы для выполнения действий в окне чата.
# Изменение параметров, выбор опций...

import re
import json
import random
import string
from datetime import datetime, date
from telebot import types

from django.conf import settings

from schedule.models import BusStop, Schedule, Holiday
from tbot.models import IdsForName

from utils.translation import get_day_string, get_day_number
from tbot.services.functions import date_now


def time_generator(time_marks, start_time, duration) -> list:
    """Генератор временных меток, возвращающий временные метки из списка.
    Принимает список временных меток, стартовое время и продолжительность в минутах.
    Возвращает временные метки из списка, начиная со стартового времени, пока не пройдет
    указанное количество минут. Если время переходит через 00:00, продолжает считать.
    Рассматривая таким образом список закольцованным, а отрезок времени накладывается
    по периметру кольца, возвращая метки, которые накрыты отрезком.
    """
    def dif_to_minutes(time1, time2):
        """Разница в минутах между двумя значениями времени в формате datetime.time"""
        # Преобразование в объекты datetime.datetime
        datetime1 = datetime.combine(date.today(), time1)
        datetime2 = datetime.combine(date.today(), time2)
        # Вычисление разницы в минутах
        difference = datetime1 - datetime2
        return difference.total_seconds() / 60

    if not time_marks:
        return []
    # Находим индекс временной метки, с которой начнем генерацию
    index = None
    for time in time_marks:
        if time >= start_time:
            index = time_marks.index(time)
            break
    index = 0 if index is None else index

    counter = 0  # Счетчик минут
    time = datetime.strptime('23:59', '%H:%M').time()

    while True:
        if time_marks[index] > start_time:
            # Если следующее время больше стартового, то еще не было перехода через 00:00
            # Добавляем минуты между временами в счетчик
            counter += dif_to_minutes(time_marks[index], start_time)
            start_time = time_marks[index]
        else:
            # Если следующее время меньше стартового, значит был переход через 00:00
            # Добавляем минуты между временем и 00:00
            counter += dif_to_minutes(time, start_time) + 1
            # Добавляем минуты между 00:00 и новым временем
            counter += time_marks[index].hour * 60 + time_marks[index].minute
            start_time = time_marks[index]
        index = (index + 1) % len(time_marks)  # Переход к следующему времени (закольцованный список)
        if counter > duration:
            # Если счетчик превысил продолжительность, то выходим из цикла
            return
        yield start_time  # Возвращаем время


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
            self.key_name = IdsForName.get_name_by_id(self.key_name)  # Получаем имя по идентификатору
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
        Для идентификации клавиш использует идентификатор, вместо имени, поскольку длинные имена
        не допустимы в качестве идентификатора кнопки в телеграмме.
        Идентификаторы хранятся в таблице IdsForName. И возвращаются вместо имен.
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
        keyboard = types.InlineKeyboardMarkup(row_width=row)
        buttons = []
        for name, selected in name_dict.items():
            sel = '⚡️ ' if selected else ''
            id_name = IdsForName.get_id_by_name(name)  # Получаем идентификатор по имени
            button = types.InlineKeyboardButton(text=sel+name, callback_data=f'{kd_id}_{id_name}')
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
            self.kb_wait = [self.keyboard('🚩 🚩 🚩 Выберите остановку отправления:', stops, row=2)]

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
            self.kb_wait = [self.keyboard('🚩 🚩 🚩 Выберите остановку назначения:', for_kb, row=2)]
            self.other_fields['start'] = self.key_name  # Сохраняем начальную остановку

        if self.stage == 2:
            # ---------------- 3 этап - сохранение маршрута ----------------
            # Находим объекты остановок по названиям и направлению
            start_name = self.other_fields['start']
            bs_dict = BusStop.get_routers_by_two_busstop(start_name, self.key_name)
            try:
                # Сохраняем id начальной остановки
                self.other_fields['start'] = bs_dict['start'].external_id
                # Список автобусов на остановке
                buses = bs_dict['start'].get_bus_by_stop()
            except AttributeError:
                # Если остановка не найдена, то выводим сообщение и завершаем действие
                self.bot.send_message(self.message.chat.id, '⚠️ Возможно между этими остановками нет прямого маршрута. '
                                                            'Попробуйте выбрать другие остановки.')
                self.stage = 0
                return

            # Автосохранение маршрута
            favorites = json.loads(self.user.parameter.favorites)
            base_name = f'{start_name} - {self.key_name}'
            name = base_name
            i = 1
            while name in favorites:
                name = f'{base_name} {str(i)}'
                i += 1

            # Составляем строку для сообщения
            string = (f'🚥 На остановке "{bs_dict["start"].name}"\nостанавливаются следующие автобусы:\n' +
                      ', '.join([str(bus.number) for bus in buses]) +
                      f'.\n\n🚥 Из них, по выбранному вами маршруту, до остановки "{self.key_name}" идут автобусы:\n' +
                      ', '.join([str(bus.number) for bus in bs_dict['buses']]))

            # Отправляем сообщение со списком автобусов и приглашением ввести имя для сохранения
            self.bot.send_message(self.message.chat.id, string)
            self.bot.send_message(self.message.chat.id, f'💾 Маршрут сохранен в Мои маршруты под именем:\n"{name}"')

            # Сохраняем параметры
            self.other_fields['finish'] = bs_dict['finish'].external_id
            self.other_fields['check'] = [bus.number for bus in bs_dict['buses']]  # Список автобусов которые будут сохранены как выбранные

            # Сохраняем маршрут в Избранное (favorites)
            save = json.loads(self.user.parameter.favorites)
            save[name] = {'start': self.other_fields['start'], 'finish': self.other_fields['finish'],
                          'check': self.other_fields['check']}
            self.user.parameter.favorites = json.dumps(save, ensure_ascii=False)
            self.user.parameter.save()

        self.stage += 1


class MyRouter(Executor):
    """Выводит список сохраненных маршрутов.
    Предоставляет выбор маршрута.
    Отображает расписание на начальной остановке маршрута."""

    def execute(self):
        """Показывает короткое расписание автобусов на выбранной остановке."""
        if self.stage == 0:
            # ---------------- 1 этап - запрос маршрута ----------------
            # Выводим список маршрутов из Избранного
            favorites = json.loads(self.user.parameter.favorites)
            if not favorites:
                self.bot.send_message(self.message.chat.id, '⚠️ У вас нет сохраненных маршрутов.')
                return
            self.kb_wait = [self.keyboard('🚌 Выберите маршрут:', favorites.keys(), row=1)]

        if self.stage == 1:
            # ---------------- 2 этап - вывод расписания ----------------
            # Засчитываем пользователю получение расписания
            self.user.schedule_count += 1
            self.user.save()

            week = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
            # Текущий день недели (1-7), если дата переопределена в таблице,
            # вернет значение из нее, иначе текущий день недели
            day = Holiday.is_today_holiday()
            day = day if day else datetime.now().isoweekday()

            count = None  # Указывает на то, что не нужно выводить расписание за сутки дня
            check = None  # Список автобусов, которые будут выводиться

            # Получаем данные о маршруте
            favorites = json.loads(self.user.parameter.favorites)
            if self.key_name in favorites:
                # Сохраняем выбранный маршрут
                self.other_fields['rout'] = self.key_name

            key_name = self.other_fields['rout']
            if check is None:
                # Если список автобусов уже не определен
                check = favorites[key_name]['check']

            # Находим объект остановки по id
            start = favorites[key_name]['start']
            start = BusStop.objects.get(external_id=start)

            # Определяем текущее время с поправкой на часовой пояс
            time_now = date_now().time()  # конвертируем время в текущий часовой пояс

            # Вид отображения расписания
            mode = favorites[key_name].get('view', 'По времени')

            # Возможно передан день недели из дополнительной клавиатуры.
            # Значит выводим полное расписание остановки за выбранный день.
            if self.key_name in week:
                count = '24 часа'
                day = get_day_number(self.key_name)  # Получаем номер дня недели
                buses_obj = start.get_bus_by_stop()  # Получаем список автобусов на остановке
                check = [bus.number for bus in buses_obj]  # В данном случае показываем все
                time_now = datetime.strptime('03:00', '%H:%M').time()  # Время начала дня
                mode = 'По автобусам'

            # За какой промежуток времени выводить расписание
            if count is None:
                count = favorites[key_name].get('count', '30 минут')
            delta = {
                '15 минут': 15,
                '30 минут': 30,
                '1 час': 60,
                '2 часа': 120,
                '3 часа': 180,
                '24 часа': 1440
            }

            # Для каждого автобуса в списке из favorites.
            # Найдем в модели Schedule 2 записи с этим автобусом и остановкой start после текущего времени.
            # Отсортируем по времени и сохраним в словарь по автобусу.

            # От способа отображения зависит способ сборки данных и вывода.
            # Для вида По автобусам создаем словарь {автобус: [время1, время2 (в datetime)]}
            # Для вида По времени создаем словарь {время (в datetime): [автобус1, автобус2]}
            schedule = dict()
            for bus in check:
                # Находим записи в расписании
                sch = Schedule.objects.filter(
                    bus_stop=start, bus__number=bus, day=day).order_by('time')
                if len(sch) == 0:  # Если записей нет, переходим к следующему автобусу
                    continue
                if mode == 'По времени':
                    # Сохраняем в словарь
                    for time_obj in sch:
                        if time_obj.time not in schedule:
                            schedule[time_obj.time] = [bus]
                        else:
                            schedule[time_obj.time].append(bus)
                    # Сортируем по времени
                    schedule = dict(sorted(schedule.items(), key=lambda x: x[0]))
                    gen = time_generator(list(schedule), time_now, delta[count])
                    schedule = {time: schedule[time] for time in gen}
                else:
                    # Сохраняем в словарь
                    gen = time_generator([time_obj.time for time_obj in sch], time_now, delta[count])
                    times = [time for time in gen]
                    if times:
                        schedule[bus] = times

            # Выводим только count временных отметок для каждого автобуса в режиме По автобусам
            # В режиме По времени выводим только count временных отметок
            string = f'🚌 Маршрут *"{key_name}"*\nот остановки *"{start.name}"*\nна период *{count}*   ({get_day_string(day)})\n\n'
            if not schedule:
                if count == '24 часа':
                    string += 'Автобусы уже не ходят.\n'
                else:
                    string += f'⚠️ Нет автобусов на период - *{count}*.\n'
            if mode == 'По автобусам':
                for bus, times in schedule.items():
                    string += f'*Автобус №{bus}*  -  {",  ".join(time.strftime("%H:%M") for time in times)}\n\n'
            else:
                for time, buses in schedule.items():
                    string += f'{time.strftime("%H:%M")}  -  '
                    buses = [f'№{bus}' for bus in buses]
                    string += f'{",  ".join(buses)}\n'

            # Отправляем расписание
            self.bot.send_message(self.message.chat.id, string, parse_mode='Markdown')

            # Формируем клавиатуру для дополнительных действий
            self.kb_wait = [self.keyboard(f'📆 Полное расписание на любой день:', week, row=7)]
        self.stage = 1


class MyRouterSetting(Executor):
    """Редактирование маршрутов в Избранном.
    Выводит список маршрутов, предоставляет выбор маршрута для редактирования.
    Позволяет настроить:
        - Выбор автобусов
        - Отображение расписания (по времени или по автобусам)
        - Количество ближайших автобусов
        - Переименовать маршрут
        - Удалить маршрут
    """
    def make_checking_dict_by_list(self, ful_list: list, check_list: list):
        """Создает словарь из полного списка элементов (ключи),
        со значениями True для элементов во втором списке,
        и False для остальных.
        Возвращает словарь {элемент: True/False}.
        """
        check_dict = dict()
        for item in ful_list:
            if item in check_list:
                check_dict[item] = True
            else:
                check_dict[item] = False
        return check_dict

    def make_bus_list_by_buss(self, busstop_id: str):
        """Создает словарь автобусов с помеченными (выбранными).
        Принимает id остановки
        Список автобусов берет из Избранного пользователя.
        Возвращает словарь {автобус: True/False}.
        """
        bus_stop = BusStop.objects.get(external_id=busstop_id)
        buses_obj = bus_stop.get_bus_by_stop()
        buses = [bus.number for bus in buses_obj]
        return self.make_checking_dict_by_list(buses, self.other_fields['favorites']['check'])

    def get_favorite(self, name: str):
        """Возвращает словарь с данными о маршруте из Избранного.
        Принимает название маршрута."""
        favorites = json.loads(self.user.parameter.favorites)
        return favorites[name]

    def set_favorite(self, name: str, value):
        """Обновляет данные о маршруте в Избранном.
        Принимает название маршрута и словарь с новыми данными."""
        favorites = json.loads(self.user.parameter.favorites)
        favorites[name] = value
        self.user.parameter.favorites = json.dumps(favorites, ensure_ascii=False)
        self.user.parameter.save()

    def execute(self):
        """Показывает короткое расписание автобусов на выбранном маршруте."""
        menu = {
            'Выбор автобусов': 2.0,
            'Вид расписания': 3.0,
            'Промежуток времени': 4.0,
            'Переименовать маршрут': 5.0,
            'Удалить маршрут': 6.0
        }

        if self.stage == 10:
            # ---------------- 10 этап - определение выбора меню ----------------
            self.stage = menu[self.key_name]

        if self.stage == 0:
            # ---------------- 0 этап - запрос маршрута ----------------
            # Выводим список маршрутов из Избранного
            favorites = json.loads(self.user.parameter.favorites)
            self.kb_wait = [self.keyboard('⚙️ Редактирование маршрута:', favorites.keys(), row=1)]

            self.stage = 1

        elif self.stage == 1:
            # ---------------- 1 этап - выбор действия ----------------
            # Получаем данные о маршруте из Избранного и сохраняем их в дополнительное поле
            favorites = json.loads(self.user.parameter.favorites)
            self.other_fields['name_rout'] = self.key_name  # Сохраняем название маршрута
            self.other_fields['favorites'] = favorites[self.key_name]  # Сохраняем данные о настройках маршрута

            # Выводим клавиатуру с действиями
            self.kb_wait = [self.keyboard(f'🔧 Выберите действе для маршрута\n"{self.other_fields["name_rout"]}":',
                                          menu.keys(), row=1)]

            self.stage = 10

        elif self.stage == 2.0:
            # ---------------- 2.0 этап - вывод списка автобусов ----------------
            # Список автобусов представляется с возможностью выбора (галочка)
            buses = self.make_bus_list_by_buss(self.other_fields['favorites']['start'])
            self.kb_wait = [self.keyboard(f'🚌 Выберите автобусы для маршрута\n"{self.other_fields["name_rout"]}":',
                                          buses, row=3)]

            self.stage = 2.1

        elif self.stage == 2.1:
            # ---------------- 2.1 этап - выбор автобусов в списке  ----------------
            # Реакция на клик по автобусу
            if self.key_name in self.other_fields['favorites']['check']:
                self.other_fields['favorites']['check'].remove(self.key_name)
            else:
                self.other_fields['favorites']['check'].append(self.key_name)
                self.other_fields['favorites']['check'].sort()

            # Выводим клавиатуру с заменой предыдущей
            buses = self.make_bus_list_by_buss(self.other_fields['favorites']['start'])
            self.kb_wait = [self.keyboard(f'🚌 Выберите автобусы для маршрута\n"{self.other_fields["name_rout"]}":',
                                          buses, row=3, replace=True)]

            # Сохраняем изменения в Избранном
            self.set_favorite(self.other_fields['name_rout'], self.other_fields['favorites'])

        elif self.stage == 3.0:
            # ---------------- 3 этап - выбор вида расписания ----------------
            if 'view' in self.other_fields['favorites']:
                # Если вид расписания уже был выбран, то выводим его
                check = self.other_fields['favorites']['view']
            else:
                check = 'По времени'

            menu = self.make_checking_dict_by_list(['По времени', 'По автобусам'], [check])
            self.kb_wait = [self.keyboard(f'🌄 Вид расписания для маршрута\n"{self.other_fields["name_rout"]}":',
                                          menu, row=1)]

            self.stage = 3.1

        elif self.stage == 3.1:
            # ---------------- 3.1 этап - записать вид расписания ----------------
            # Реакция на клик по виду расписания
            menu = self.make_checking_dict_by_list(['По времени', 'По автобусам'], [self.key_name])
            self.kb_wait = [self.keyboard(f'🌄 Вид расписания для маршрута\n"{self.other_fields["name_rout"]}":', menu, row=1, replace=True)]

            # Сохраняем изменения в Избранном
            self.other_fields['favorites']['view'] = self.key_name
            self.set_favorite(self.other_fields['name_rout'], self.other_fields['favorites'])

        elif self.stage == 4.0:
            # ---------------- 4 этап - выбор количества автобусов ----------------
            if 'count' in self.other_fields['favorites']:
                # Если количество автобусов уже было выбрано, то выводим его
                check = self.other_fields['favorites']['count']
            else:
                check = '30 минут'

            menu = self.make_checking_dict_by_list(['15 минут', '30 минут', '1 час', '2 часа', '3 часа', '24 часа'], [check])
            self.kb_wait = [
                self.keyboard(f'⏰ За какой промежуток времени начиная от текущего '
                              f'показать автобусы для маршрута\n"{self.other_fields["name_rout"]}":',
                                          menu, row=2)]

            self.stage = 4.1

        elif self.stage == 4.1:
            # ---------------- 4.1 этап - записать количество автобусов ----------------
            # Реакция на клик по количеству автобусов
            menu = self.make_checking_dict_by_list(['15 минут', '30 минут', '1 час', '2 часа', '3 часа', '24 часа'], [self.key_name])
            self.kb_wait = [self.keyboard(f'За какой промежуток времени начиная от текущего '
                              f'показать автобусы для маршрута\n"{self.other_fields["name_rout"]}":',
                                          menu, row=2, replace=True)]

            # Сохраняем изменения в Избранном
            self.other_fields['favorites']['count'] = self.key_name
            self.set_favorite(self.other_fields['name_rout'], self.other_fields['favorites'])

        elif self.stage == 5.0:
            # ---------------- 5 этап - переименование маршрута ----------------
            # Отправляем сообщение с запросом нового имени
            self.bot.send_message(self.message.chat.id,
                                  f'✏️ Введите новое название для маршрута\n"{self.other_fields["name_rout"]}":')

            self.stage = 5.1

        elif self.stage == 5.1:
            # ---------------- 5.1 этап - сохранение нового имени ----------------
            # Сохраняем новое имя в Избранном с сохранением порядка
            pattern = r'[\n\r"\\]'
            if re.search(pattern, self.message.text):
                self.bot.send_message(self.message.chat.id, '⚠️ В новом названии использованы недопустимые символы, '
                                                            'пожалуйста, введите другое название.')
                return
            favorites = json.loads(self.user.parameter.favorites)
            if self.message.text in favorites:
                self.bot.send_message(self.message.chat.id, '⚠️ Маршрут с таким именем уже существует, '
                                                            'пожалуйста, введите другое название.')
                return


            favorites = json.loads(self.user.parameter.favorites)
            new_favorites = dict()
            for key, value in favorites.items():
                if key == self.other_fields['name_rout']:
                    new_favorites[self.message.text] = value
                else:
                    new_favorites[key] = value

            self.other_fields['name_rout'] = self.message.text
            self.other_fields['favorites'] = new_favorites
            self.user.parameter.favorites = json.dumps(new_favorites, ensure_ascii=False)
            self.user.parameter.save()

            self.bot.send_message(self.message.chat.id, f'💾 Маршрут "{self.message.text}" сохранен.')

            self.stage = 0

        elif self.stage == 6.0:
            # ---------------- 6 этап - удаление маршрута ----------------
            # Удаляем маршрут из Избранного
            # Подтверждение удаления
            if self.key_name != 'Удалить маршрут':
                return

            if 'del' not in self.other_fields:
                self.other_fields['del'] = 1
                self.bot.send_message(self.message.chat.id, f'❗️ Для удаления маршрута "{self.other_fields["name_rout"]}" '
                                                            'подтвердите действие, нажав повторно кнопку "Удалить маршрут" через '
                                                            '15 секунд, когда как она перестанет переливаться.')
                return

            favorites = json.loads(self.user.parameter.favorites)
            del favorites[self.other_fields['name_rout']]
            self.user.parameter.favorites = json.dumps(favorites, ensure_ascii=False)
            self.user.parameter.save()

            self.bot.send_message(self.message.chat.id, f'❗️Маршрут "{self.other_fields["name_rout"]}" удален.')

            self.stage = 0


class ExeMessage(Executor):
    """Прием сообщений от пользователей.
    Этот класс работает, когда пользователь отправляет команду /message."""

    def execute(self):
        """Принимает сообщение от пользователя и передает администратору.
        Если сообщение начинается с Answer_to_, то это ответ на сообщение.
        Ответ отправляется в чат с указанным id."""
        text = self.message.text
        chat_id = self.message.chat.id
        user_id = self.message.from_user.id

        # Если в начале текста Answer_to_ ... - это ответ на сообщение
        # Берем первое слово, оно состоит из Answer_to_dddd,
        # где dddd - id чата в который отвечаем, далее сообщение
        if text.startswith('Answer_to_'):
            # Разделяем первым пробелом сообщение на 2 части
            chat_id, text = text.split(' ', 1)
            chat_id = int(chat_id.split('_')[2])
            self.bot.send_message(chat_id, f'От разработчика:\n{text}')
            ok = '📨 Сообщение отправлено'
        else:
            # Преобразуем строку JSON в список (это id администраторов)
            admin_ids = settings.ADMINS

            # Отправляем сообщение каждому администратору
            for admin_id in admin_ids:
                self.bot.send_message(admin_id, f"📨 Пользователь с ID {user_id} и ID чата {chat_id} отправил сообщение: \n{text}")
                self.bot.send_message(admin_id, f"Answer_to_{chat_id} ")

            ok = "📨 Ваше сообщение отправлено разработчику. Благодарим за обратную связь!"

        self.bot.send_message(self.message.chat.id, ok)