# Классы для выполнения действий в окне чата.
# Изменение параметров, выбор опций...

import re
import json
import random
import string
import logging
from telebot import types
from datetime import datetime
from functools import cmp_to_key

from django.conf import settings

from tbot.models import IdsForName
from schedule.models import BusStop, Schedule, Holiday, StopGroup
from schedule.services.timestamp import route_analysis, time_generator, preparing_bus_list, answer_by_two_busstop
from utils.translation import get_day_string, get_day_number
from utils.sorted_buses import compare_name, sorted_buses
from tbot.services.functions import date_now
from schedule.services.full_schedule import full_schedule

logger = logging.getLogger('alisa')

class Executor:
    """Базовый класс для выполнения действий в окне чата.
    Устанавливает общие аттрибуты для всех действий при начале,
    восстанавливает их при продолжениях, и имеет метод для сохранения.
    """

    def __init__(self, bot, user, bot_object, action=None):
        """
        Пояснения по клавиатурам: они могут быть постоянными и временными.
        Постоянные - это те, которые всегда активны в чате, имеют свой id и класс (класс знает где ее обработать).
        Временные - это те, которые после срабатывания уже не доступны, их id меняется.
        Постоянные имеют приоритет и запрос от них передается их классу обработчику сразу
        (для них не хранятся временные параметры передаваемые на дальнейшие этапы выполнения программы).
        id постоянных клавиатур хранятся в таблице IdsForName, одна для класса.
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
        self.kb_wait = data.get('kb_id', [])  # ids временных клавиатур от которых ожидаем ответа
        self.other_fields = data.get('other_fields', dict())  # Дополнительные поля

        # Получим название класса и запишем его в БД
        user.parameter.class_name = self.__class__.__name__
        user.parameter.save()
        self.answer = self.execute()  # Выполняем действие и получаем ответ что делали

        if self.answer:
            self.save()  # Сохраняем параметры выполнения программы в БД

    def execute(self):
        """Выполняет действие. В классах - наследниках переопределяется.
        Они должны вернуть что-то если выполняли действие, иначе None."""
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

    def keyboard(self, message: str, names: (list, dict), row=1, replace=False, kd_id=None):
        """Создает InlineKeyboardMarkup клавиатуру из заданного списка.
        Может вывести клавиатуру с отметками выбранных клавиш (галочка перед названием),
        для этого в качестве списка должен быть передан словарь: {name: True/False}.
        Если replace=True, заменяет клавиатуру в чате.
        Принимает: сообщение (название клавиатуры), список названий клавиш,
        количество клавиш в строке и флаг замены клавиатуры, идентификатор клавиатуры (тогда он не выбирается случайно).
        Возвращает: идентификатор клавиатуры. Он фигурирует в названии клавиш: идентификатор_название.
        Выводит клавиатуру в чат.
        Для идентификации клавиш использует идентификатор, вместо имени, поскольку длинные имена
        не допустимы в качестве идентификатора кнопки в телеграмме.
        Идентификаторы хранятся в таблице IdsForName. И возвращаются вместо имен.
        """
        if kd_id is None:
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
            button = types.InlineKeyboardButton(text=sel + name, callback_data=f'{kd_id}_{id_name}')
            buttons.append(button)

        # Добавляем кнопки в разметку заданное количество раз в строке
        for i in range(0, len(buttons), row):
            keyboard.add(*buttons[i:i + row])
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
        answer = None
        if self.stage == 0:
            # ---------------- 1 этап - запрос остановки ----------------
            # Составим список остановок без повторений, в алфавитном порядке
            stops = BusStop.get_all_bus_stops_names()

            # Отправляем сообщение с клавиатурой и запоминаем ее id
            self.kb_wait = [self.keyboard('🚩 🚩 🚩 Выберите остановку отправления:', stops, row=2)]
            answer = f'{self.__class__.__name__} - {self.stage}'

        # Дальнейшие этапы выполняются при ответах от нужных клавиатур
        run = True if self.kb_id in self.kb_wait else False

        if run and self.stage == 1:
            # ---------------- 2 этап - запрос направления ----------------
            # Составим список остановок без повторений, в алфавитном порядке
            for_kb = BusStop.get_all_bus_stops_names()

            # Отправляем сообщение с клавиатурой
            self.kb_wait = [self.keyboard('🚩 🚩 🚩 Выберите остановку назначения:', for_kb, row=2)]
            self.other_fields['start'] = self.key_name  # Сохраняем начальную остановку
            answer = f'{self.__class__.__name__} - {self.stage}'

        if run and self.stage == 2:
            # ---------------- 3 этап - сохранение маршрута ----------------
            # Находим объекты остановок по названиям и направлению
            # Тех, что идут с остановок отправления на остановки прибытия
            start_name = self.other_fields['start']
            finish_name = self.key_name

            try:
                # Формируем группы названий остановок отправления и прибытия
                stops_lists = StopGroup.get_group_by_stop_name(start_name, finish_name)
            except ValueError:
                # Выбрана одна остановка для отправления и прибытия
                self.bot.send_message(self.message.chat.id, '⚠️ Выберите разные остановки для отправления и прибытия.')
                self.stage = 0
                return f'{self.__class__.__name__} - {self.stage}'

            start_list = stops_lists["start_names"]  # Названия остановок отправления

            # Находим все автобусы которые выходят из остановок отправления
            buses = BusStop.get_bus_by_stop(start_list)

            # Определяем автобусы, которые идут по нужному маршруту
            # с любой из остановок отправления на любую остановку прибытия
            # Собираем их в словарь по остановкам отправления со списком
            # номеров автобусов для каждой.

            # Получаем список словарей со всеми автобусами, для каждого сочетания
            # остановок отправления и прибытия
            analysis = route_analysis(start_name, finish_name)

            # Преобразуем словарь с ключами из названий остановок: start - finish.
            # А в значениях списки автобусов.
            # Одновременно фильтруем по приоритету, оставляем только 1 и 2
            bs_dict = {}
            for item in analysis:
                if item['priority'] not in [1, 2]:
                    continue  # Фильтр по приоритету
                name = f"{item['start'].name} - {item['finish'].name}"
                bus = item['bus'].number
                if name not in bs_dict:
                    bs_dict[name] = [bus]
                else:
                    bs_dict[name].append(bus)
            # Удаляем дубликаты, сортируем
            for key, value in bs_dict.items():
                bs_dict[key] = sorted_buses(set(value))

            if not bs_dict:
                self.bot.send_message(self.message.chat.id, '⚠️ Между этими остановками нет прямого маршрута. '
                                                            'Попробуйте выбрать другие остановки.')
                self.stage = 0
                return f'{self.__class__.__name__} - {self.stage}'
            
            # Автосохранение маршрута
            favorites = json.loads(self.user.parameter.favorites)
            base_name = f'{start_name} - {finish_name}'
            name = base_name
            i = 1
            # Ищем свободное название маршрута
            while name in favorites:
                name = f'{base_name} {str(i)}'
                i += 1

            # Составляем строку для сообщения
            string = (f"🚥 На остановках {', '.join(start_list)} останавливаются следующие автобусы:\n" +
                      f', '.join([str(bus.number) for bus in buses]) +
                      f'.\n\n🚌 Вам подходят автобусы:\n')
            select_buses = set()
            for bs_name, buses_list in bs_dict.items():
                string += f'🚥 {bs_name}:\n' + ", ".join(buses_list) + "."
                select_buses.update(buses_list)

            select_buses = list(select_buses)
            logger.warning(f'Пользователь {self.user.user_name} {self.user.user_id} добавил маршрут "{base_name}".')

            # Отправляем сообщение со списком автобусов и приглашением ввести имя для сохранения
            self.bot.send_message(self.message.chat.id, string)
            self.bot.send_message(self.message.chat.id, f'💾 Маршрут сохранен в Мои маршруты под именем:\n"{name}"')

            # Сохраняем параметры
            self.other_fields['finish'] = finish_name

            # Сохраняем маршрут в Избранное (favorites)
            save = json.loads(self.user.parameter.favorites)
            save[name] = {'start': self.other_fields['start'], 'finish': self.other_fields['finish']}
            self.user.parameter.favorites = json.dumps(save, ensure_ascii=False)
            self.user.parameter.save()
            answer = f'{self.__class__.__name__} - {self.stage}'

        self.stage += 1

        return answer


class MyRouter(Executor):
    """Выводит список сохраненных маршрутов.
    Предоставляет выбор маршрута.
    Отображает расписание на начальной остановке маршрута."""

    def execute(self):
        """Показывает короткое расписание автобусов на выбранной остановке."""
        answer = None
        if self.__class__.__name__ == IdsForName.get_name_by_id(self.kb_id) or self.kb_id in self.kb_wait:
            # Запрос от постоянной клавиатуры или от дополнительной (под расписанием) -
            # сразу переходим к показу информации
            self.stage = 1

        if self.stage == 0:
            # ---------------- 1 этап - запрос маршрута ----------------
            # Выводим список маршрутов из Избранного
            favorites = json.loads(self.user.parameter.favorites)
            if not favorites:
                self.bot.send_message(self.message.chat.id, '⚠️ У вас нет сохраненных маршрутов.')
                return f'{self.__class__.__name__} - {self.stage}'

            # Это постоянная клавиатура, она имеет один id и всегда приводит в этот класс
            # запоминаем ее если она еще не была запомнена
            id_const_kb = str(IdsForName.get_id_by_name(self.__class__.__name__))
            self.kb_wait = [self.keyboard('🚌 Выберите маршрут:', favorites.keys(), row=1, kd_id=id_const_kb)]

            answer = f'{self.__class__.__name__} - {self.stage}'
            self.stage = 1
            return answer

        if not self.kb_id:
            return answer  # Тут не обрабатываем запросы не от клавиатуры

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

            count = None  # Указывает на то, что не нужно выводить расписание за сутки

            # Получаем данные о маршруте
            favorites = json.loads(self.user.parameter.favorites)
            if self.key_name in favorites:
                # Сохраняем выбранный маршрут
                self.other_fields['rout'] = self.key_name

            key_name = self.other_fields['rout']
            logger.warning(f'Пользователь {self.user.user_name} {self.user.user_id} посмотрел маршрут "{key_name}".')
            print(f'Пользователь {self.user.user_name} {self.user.user_id} посмотрел маршрут "{key_name}".')

            # Получаем названия сохраненных остановок
            start = favorites[key_name].get('start', None)
            finish = favorites[key_name].get('finish', None)

            # Определяем текущее время с поправкой на часовой пояс
            time_now = date_now().time()  # конвертируем время в текущий часовой пояс

            # Вид отображения расписания
            mode = 'time'  # По времени, для ближайших автобусов

            # ----------------------------------------------------------
            # Возможно передан день недели из дополнительной клавиатуры.
            # Значит выводим полное расписание остановки за выбранный день.
            if self.key_name in week:
                mode = 'bus'  # По автобусам, для полного расписания
                schedule = full_schedule(start, week.index(self.key_name) + 1)

                # Устанавливаем максимальную длину сообщения для Telegram API.
                # Это ограничение составляет 4096 символов.
                TELEGRAM_LIMIT = 4096

                spece = None
                # Формируем заголовок сообщения. Он будет отправлен в самом начале.
                text = f"🚌 Все автобусы от {start} на период 24 часа ({self.key_name})"

                # Начинаем итерацию по расписанию автобусов.
                for bus, routers_times in schedule.items():
                    # Создаем строку для информации о текущем автобусе.
                    bus_content = ""
                    if spece != bus.number:
                        spece = bus.number
                        # Добавляем двойной перенос строки для визуального разделения информации о разных автобусах.
                        bus_content += "\n\n"

                    # Добавляем номер автобуса.
                    bus_content += "🚌 №" + bus.number
                    # Добавляем информацию о маршрутах и времени.
                    for routers, times in routers_times.items():
                        bus_content += "\n" + ', '.join([f"*{router.start.name} - {router.end.name}*" for router in routers[:-1]])
                        bus_content += "\n" + ', '.join([time.strftime("%H:%M") for time in times])

                    # Проверяем, превысит ли общая длина сообщения лимит,
                    # если мы добавим информацию о текущем автобусе.
                    if len(text) + len(bus_content) > TELEGRAM_LIMIT:
                        # Если лимит будет превышен, отправляем уже накопленный текст.
                        self.bot.send_message(self.message.chat.id, text, parse_mode='Markdown')
                        # Начинаем новое сообщение с информации о текущем автобусе.
                        # .lstrip() удаляет возможные пробелы или переносы строк в начале.
                        text = bus_content.lstrip()
                    else:
                        # Если лимит не превышен, просто добавляем информацию к текущему сообщению.
                        text += bus_content

                # После завершения цикла отправляем оставшийся текст,
                # который еще не был отправлен.
                if text:
                    self.bot.send_message(self.message.chat.id, text, parse_mode='Markdown')

            # ----------------------------------------------------------
            # Нужно показать ближайшие автобусы
            if mode == 'time':
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

                try:
                    # Расписание автобусов на остановках отправления
                    # Формат возвращаемого словаря в файле
                    # "Логика поиска остановок и автобусов на них.txt"
                    schedule = answer_by_two_busstop(start, finish)
                except:
                    # Если остановка не найдена, то выводим сообщение и завершаем действие
                    return (f'Что-то пошло не так. Советую пересоздать маршрут.')

                time_now = date_now().time()  # Получаем текущее время в нужном часовом поясе
                # Перебираем полученные временные метки
                gen = time_generator(list(schedule), time_now, delta[count])
                rout = ""
                if  f"{start} - {finish}" != key_name:
                    rout = f'("{start}" - "{finish}")\n'
                text = f'🔄  Маршрут "{key_name}"\n{rout}Автобусы на период {count} ({week[day]})\n\n'
                text_list = ""
                for time in gen:
                    # Готовим словарь для вывода
                    time_str = time.strftime("%H:%M")  # Время отправления автобуса (str)
                    text_list += f'⌚ {time_str}     '  # Надцать часов минут

                    # Подготовка списка автобусов
                    text_list += "Автобус №" + preparing_bus_list(schedule[time], start)
                if not text_list:
                    text_list = f'⚠️ Нет автобусов на период - *{count}*.'

                # Отправляем расписание
                self.bot.send_message(self.message.chat.id, text + text_list, parse_mode='Markdown')

            # Формируем клавиатуру для дополнительных действий
            self.kb_wait = [self.keyboard(f'📆 Полное расписание:', week, row=7)]
            answer = f'{self.__class__.__name__} - {self.stage}'

        self.stage = 3

        return answer


class MyRouterSetting(Executor):
    """Редактирование маршрутов в Избранном.
    Выводит список маршрутов, предоставляет выбор маршрута для редактирования.
    Позволяет настроить:
        - Выбор автобусов (Отключено)
        - Отображение расписания (по времени или по автобусам) (отключено)
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
        answer = None
        menu = {
            # 'Выбор автобусов': 2.0,
            # 'Вид расписания': 3.0,
            'Промежуток времени': 4.0,
            'Переименовать маршрут': 5.0,
            'Удалить маршрут': 6.0
        }

        # Запрос от постоянной клавиатуры (это вместо self.stage == 1)
        if self.__class__.__name__ == IdsForName.get_name_by_id(self.kb_id):
            # ---------------- 1 этап - вывод меню для выбора действия ----------------
            # Получаем данные о маршруте из Избранного и сохраняем их в дополнительное поле
            favorites = json.loads(self.user.parameter.favorites)
            self.other_fields['name_rout'] = self.key_name  # Сохраняем название маршрута
            self.other_fields['favorites'] = favorites[self.key_name]  # Сохраняем данные о настройках маршрута

            # Выводим клавиатуру с действиями
            self.kb_wait = [self.keyboard(f'🔧 Выберите действе для маршрута\n"{self.other_fields["name_rout"]}":',
                                          menu.keys(), row=1)]
            self.stage = 10
            return f'{self.__class__.__name__} - {self.stage}'

        if self.stage == 0:
            # ---------------- 0 этап - запрос маршрута ----------------
            # Выводим список маршрутов из Избранного
            favorites = json.loads(self.user.parameter.favorites)

            # Это постоянная клавиатура, она имеет один id и всегда приводит в этот класс
            # запоминаем ее если она еще не была запомнена
            id_const_kb = str(IdsForName.get_id_by_name(self.__class__.__name__))
            self.kb_wait = [self.keyboard('⚙️ Редактирование маршрута:',
                                          favorites.keys(), row=1, kd_id=id_const_kb)]
            self.stage = 1
            return f'{self.__class__.__name__} - {self.stage}'

        if self.stage == 5.1:
            # ---------------- 5.1 этап - сохранение нового имени ----------------
            # Сохраняем новое имя в Избранном с сохранением порядка
            # Имя воспримет любое, ввод текста или нажатие клавиши основного меню
            pattern = r'[\n\r"\\]'
            if re.search(pattern, self.message.text):
                self.bot.send_message(self.message.chat.id, '⚠️ В новом названии использованы недопустимые символы, '
                                                            'пожалуйста, введите другое название.')
                return f'{self.__class__.__name__} - {self.stage}'
            favorites = json.loads(self.user.parameter.favorites)
            if self.message.text in favorites:
                self.bot.send_message(self.message.chat.id, '⚠️ Маршрут с таким именем уже существует, '
                                                            'пожалуйста, введите другое название.')
                return f'{self.__class__.__name__} - {self.stage}'

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
            return f'{self.__class__.__name__} - {self.stage}'

        if self.kb_id not in self.kb_wait:
            # Допускаются только запросы от клавиатур, которые ожидаются
            return None

        if self.stage == 10:
            # ---------------- 10 этап - определение выбора меню ----------------
            self.stage = menu[self.key_name]
            answer = f'{self.__class__.__name__} - {self.stage}'

        if self.stage == 2.0:
            # ---------------- 2.0 этап - выбор автобусов ----------------
            # (отключено не исправлялось под новый алгоритм)

            if self.key_name not in menu:
                # Реакция на клик по автобусу в списке если пришли не из меню
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
            # ---------------- 3.0 этап - выбор вида расписания ----------------
            # (отключено не исправлялось под новый алгоритм)

            if self.key_name in menu:
                if 'view' in self.other_fields['favorites']:
                    # Если вид расписания определен, то выводим его
                    self.key_name = self.other_fields['favorites']['view']
                else:
                    self.key_name = 'По времени'

            # Подготовка меню к выводу с учетом выбора
            menu = self.make_checking_dict_by_list(['По времени', 'По автобусам'], [self.key_name])
            # Вывод клавиатуры с заменой предыдущей
            self.kb_wait = [self.keyboard(f'🌄 Вид расписания для маршрута\n"'
                                          f'{self.other_fields["name_rout"]}":', menu, row=1, replace=True)]

            # Сохраняем изменения в Избранном
            self.other_fields['favorites']['view'] = self.key_name
            self.set_favorite(self.other_fields['name_rout'], self.other_fields['favorites'])

        elif self.stage == 4.0:
            # ---------------- 4.0 этап - выбор промежутка времени ----------------
            if self.key_name in menu:
                if 'count' in self.other_fields['favorites']:
                    # Если количество автобусов уже было выбрано, то выводим его
                    self.key_name = self.other_fields['favorites']['count']
                else:
                    self.key_name = '30 минут'  # По умолчанию

            # Реакция на клик по количеству автобусов
            menu = self.make_checking_dict_by_list(['15 минут', '30 минут', '1 час', '2 часа', '3 часа', '24 часа'],
                                                   [self.key_name])
            self.kb_wait = [self.keyboard(f'За какой промежуток времени начиная от текущего '
                                          f'показат автобусы для маршрута\n"{self.other_fields["name_rout"]}":',
                                          menu, row=2, replace=True)]

            # Сохраняем изменения в Избранном
            self.other_fields['favorites']['count'] = self.key_name
            self.set_favorite(self.other_fields['name_rout'], self.other_fields['favorites'])

        elif self.stage == 5.0:
            # ---------------- 5 этап - переименование маршрута ----------------
            # Отправляем сообщение с запросом нового имени
            self.bot.send_message(self.message.chat.id,
                                  f'✏️ Введите новое название для маршрута\n"{self.other_fields["name_rout"]}":')

            self.stage = 5.1  # 5.1 вначале, для допуска ввода с клавиатуры

        elif self.stage == 6.0:
            # ---------------- 6 этап - удаление маршрута ----------------
            # Удаляем маршрут из Избранного
            # Подтверждение удаления
            if self.key_name != 'Удалить маршрут':
                return answer

            if 'del' not in self.other_fields:
                self.other_fields['del'] = 1
                self.bot.send_message(self.message.chat.id,
                                      f'❗️ Для удаления маршрута "{self.other_fields["name_rout"]}" '
                                      'подтвердите действие, нажав повторно кнопку "Удалить маршрут"')
                return answer

            favorites = json.loads(self.user.parameter.favorites)
            del favorites[self.other_fields['name_rout']]
            self.user.parameter.favorites = json.dumps(favorites, ensure_ascii=False)
            self.user.parameter.save()

            self.bot.send_message(self.message.chat.id, f'❗️Маршрут "{self.other_fields["name_rout"]}" удален.')

            self.stage = 0

        return answer


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
                self.bot.send_message(admin_id,
                                      f"📨 Пользователь с ID {user_id} и ID чата {chat_id} отправил сообщение: \n{text}")
                self.bot.send_message(admin_id, f"Answer_to_{chat_id} ")

            ok = "📨 Ваше сообщение отправлено разработчику. Благодарим за обратную связь!"

        self.bot.send_message(self.message.chat.id, ok)

        return f'{self.__class__.__name__} - 0'
