# Модуль генерирует набор данных для создания ответа
import re
import itertools
from datetime import date
from datetime import datetime
from typing import Dict, List, Any

from tbot.services.functions import date_now
from schedule.models import BusStop, Bus, Router, Order, Schedule, Holiday, StopGroup
from .functions import format_bus_number


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


def route_analysis(start_stop_name: str, finish_stop_name: str) -> List:
    """Анализ маршрутов, определение приоритетов маршрутов.
    Находит все автобусы, которые идут от каждой остановки
    отправления к каждой остановке прибытия. Определяет наиболее
    релевантные автобусы, для каждого случая и назначает приоритет -
    т.е. удобство добраться этим автобусом.

    Args: 
        start_stop_name - остановка отправления
        finish_stop_name - остановка прибытия

    Returns:
        [
            {
                "priority": priority,                       (приоритет)
                "bus": bus,                                 (автобус)
                "start": start_bus_stop,                    (остановка отправления)
                "finish": finish_bus_stop,                  (остановка прибытия)
                "final_stop_start": analysis_part[0],       (конечная, откуда едет)
                "final_stop_finish": analysis_part[-1],     (конечная, куда едет)
            }
        ]

        Пустой список вернет если нет автобусов или 
        остановки отправления и прибытия одноименные.
    """
    # 1 --------------------------------
    # Формируем группы остановок. Логика полностью переписана в соответствии
    # с реальной структурой модели StopGroup (JSON-поле list_name).
    names = StopGroup.get_group_by_stop_name(start_stop_name, finish_stop_name)
    start_list = names["start_names"]  # Получаем остановки из групп
    finish_list = names["finish_names"]  # Получаем остановки из групп

    # 2 --------------------------------
    # Получаем объекты BusStop для всех найденных названий.
    start_objects = list(BusStop.objects.filter(name__in=start_list))
    finish_objects = list(BusStop.objects.filter(name__in=finish_list))

    # print(start_objects)
    # print(finish_objects)

    # 3 --------------------------------
    # Получаем все маршруты для автобусов, проходящих через начальные остановки.
    # ВАЖНО: Реализовано без оптимизации (с циклами) для целей тестирования.
    bus_to_stops = {}
    all_buses = Bus.objects.filter(routers__orders_for_router__bus_stop__in=start_objects).distinct()

    for bus in all_buses:
        routes = Router.objects.filter(bus=bus)
        bus_parts = []
        for route in routes:
            part_orders = Order.objects.filter(router=route).order_by('order_number')
            bus_parts.append([order.bus_stop for order in part_orders])
        bus_to_stops[bus] = bus_parts

    # for part, it in bus_to_stops.items():
    #     print(part, "\n", it, "\n")

    # 4 --------------------------------
    # Итерация, создание пар и анализ маршрутов.
    # Сначала собираем ВСЕ возможные маршруты в `found_routes`, а в шаге 5 фильтруем.
    found_routes = []
    for bus, parts in bus_to_stops.items():
        # Перебираем автобусы и части маршрута (туда и обратно)
        for start_bus_stop, finish_bus_stop in itertools.product(start_objects, finish_objects):
            # Перебираем комбинации остановок

            # Есть ли остановка прибытия в маршруте
            is_finish_on_route = any(finish_bus_stop in part for part in parts)
            if not is_finish_on_route:
                continue

            priority = 4
            analysis_part = None

            if len(parts) == 2:
                # Остановки отправления и прибытия находятся в разных частях
                # (направлениях) маршрута
                is_start_in_part1 = start_bus_stop in parts[0]
                is_finish_in_part1 = finish_bus_stop in parts[0]
                is_start_in_part2 = start_bus_stop in parts[1]
                is_finish_in_part2 = finish_bus_stop in parts[1]

                if (is_start_in_part1 and is_finish_in_part2) or \
                        (is_start_in_part2 and is_finish_in_part1):
                    priority = 2
                    analysis_part = parts[0] if is_start_in_part1 else parts[1]

            for part in parts:
                if start_bus_stop in part and finish_bus_stop in part:
                    # Обе остановки в одной части
                    priority = 3
                    analysis_part = part
                    try:
                        # Расположение остановок в части правильное
                        # в направлении движения от старт к финиш
                        start_index = part.index(start_bus_stop)
                        finish_index = part.index(finish_bus_stop)
                        if start_index < finish_index:
                            priority = 1
                            break
                    except ValueError:
                        continue

            if priority < 4 and analysis_part:
                # Приоритеты высокие - формируем ответ
                found_routes.append({
                    "priority": priority,
                    "bus": bus,
                    "start": start_bus_stop,
                    "finish": finish_bus_stop,
                    "final_stop_start": analysis_part[0],
                    "final_stop_finish": analysis_part[-1],
                })

    # Сохраняей вывод в файл
    with open('log.tmp', 'w', encoding='utf-8') as f:
        for item in found_routes:
            for k in item.items():
                print(k, file=f)
            print(file=f)


    return found_routes


def answer_by_two_busstop(start_stop_name: str, finish_stop_name: str) -> Dict:
    """
    Находит оптимальные маршруты автобусов между двумя остановками на основе их названий.
    Описание в файле "Логика поиска остановок и автобусов на них.txt"

    Args:
        start_stop_name: Название остановки отправления.
        finish_stop_name: Название остановки прибытия.

    Returns:
        Словарь, где ключи - время отправления, а значения - список
        вариантов маршрута на это время.
    """
    # Проводим анализ маршрутов
    found_routes = route_analysis(start_stop_name, finish_stop_name)

    # 5 --------------------------------
    # Очищаем `found_routes`, оставляя только наивысший приоритет.
    min_priority = min(route['priority'] for route in found_routes)

    if min_priority == 4:
        return {}  # Нет приоритетов выше 4 (1, 2, 3)

    # Выбираем все маршруты с высшим (из имеющихся) приоритетом
    filtered_routes = [route for route in found_routes if route['priority'] == min_priority]

    # Формируем ответ
    report = {}
    for route in filtered_routes:
        start_bus_stop = route['start']
        bus_info = {
            route['bus']: {
                "finish": route['finish'],
                "final_stop_start": route['final_stop_start'],
                "final_stop_finish": route['final_stop_finish'],
            }
        }
        if start_bus_stop not in report:
            report[start_bus_stop] = {
                "priority": route['priority'],
                "buses": bus_info
            }
        else:
            report[start_bus_stop]['buses'].update(bus_info)

    # for bus_stop, v in report.items():
    #     print("--- ", bus_stop, "\n")
    #     print("priority:", v["priority"])
    #     for bus_out, route_info in v["buses"].items():
    #         print(bus_out)
    #         print(route_info, "\n")

    # 6 --------------------------------
    # Создаем словарь timestamp с расписанием.
    # Реализовано без оптимизации для тестирования.
    timestamp = {}

    day = Holiday.is_today_holiday()
    day = day if day else datetime.now().isoweekday()
    time_now = date_now().time()

    # Для остановки отправления и другой информации по маршруту:
    # приоритет, автобусы с этой остановки, куда пребывает каждый,
    # конечные для каждого
    for start_bus_stop, data in report.items():
        # Для автобуса и информации по нему
        for bus, bus_data in data['buses'].items():
            # Получаем расписание автобуса на остановке
            # отсортированное по времени
            schedules = Schedule.objects.filter(
                bus_stop=start_bus_stop, bus=bus, day=day
            ).order_by('time')

            if not schedules:
                continue

            # Вычисляем модификатор
            for sch in schedules:
                modifiers = []
                if start_bus_stop.name != start_stop_name:
                    modifiers.append("start_deff")
                if bus_data['finish'].name != finish_stop_name:
                    modifiers.append("finish_deff")

                if data['priority'] == 2:
                    modifiers.append("final_stop_one")
                if data['priority'] == 3:
                    modifiers.append("final_stop_two")

                for other_start, other_data in report.items():
                    if start_bus_stop.name == other_start.name and start_bus_stop.id != other_start.id:
                        if bus in other_data['buses']:
                            modifiers.append("both")
                            break

                schedule_entry = {
                    "bus": bus,  # Автобус
                    "start": start_bus_stop,  # С какой остановки ехать
                    "finish": bus_data['finish'],  # На какой остановке выходить
                    "modifier": list(set(modifiers)),  # Модивикатор
                    "final_stop_start": bus_data['final_stop_start'],  # Конечные
                    "final_stop_finish": bus_data['final_stop_finish'],
                }

                # Добавляем новую временную метку с информацией по автобусу
                if sch.time not in timestamp:
                    timestamp[sch.time] = []
                timestamp[sch.time].append(schedule_entry)

    # 7 --------------------------------
    # Сортируем и фильтруем `timestamp` по времени.
    if not timestamp:
        return {}

    # Сортируем по времени
    timestamp = dict(sorted(timestamp.items(), key=lambda x: x[0]))

    try:
        gen = time_generator(list(timestamp.keys()), time_now, 1440)
        timestamp = {time: timestamp[time] for time in gen}
    except NameError:
        pass

    # 8 --------------------------------
    # Возвращаем словарь timestamp
    # for k, v in timestamp.items():
    #     print("--- ", k.strftime('%-H:%M'), " ---")
    #     print(v, "\n")
    return timestamp


def sort_buses(buses: List[Dict[str, Any]], name: str) -> List[Dict[str, Any]]:
    """
    Сортирует список автобусов по трём уровням приоритета:

    1. Автобусы, у которых bus['start'].name совпадает с заданным `name`, идут первыми.
    2. Внутри каждой группы (совпадающих и остальных):
       - сначала автобусы без модификаторов (bus['modifier'] пустой)
       - затем автобусы с модификаторами
    3. Остальные автобусы сортируются по bus['start'].id (по возрастанию)

    :param buses: Список словарей, каждый из которых описывает автобус и его маршрут.
    :param name: Название остановки, которая имеет приоритет в сортировке.
    :return: Отсортированный список словарей.
    """

    def sort_key(bus: Dict[str, Any]) -> tuple:
        """
        Генерирует ключ сортировки для каждого автобуса.

        :param bus: Словарь с данными автобуса.
        :return: Кортеж (priority, start_id), где:
                 - priority: целое число от 0 до 3, определяющее порядок:
                     0 — приоритетная остановка + без модификатора
                     1 — приоритетная остановка + с модификатором
                     2 — остальные + без модификатора
                     3 — остальные + с модификатором
                 - start_id: ID остановки, используется для сортировки остальных
        """
        is_named = bus['start'].name == name
        has_modifier = bool(bus.get('modifier'))
        start_id = bus['start'].id

        if is_named and not has_modifier:
            priority = 0
        elif is_named and has_modifier:
            priority = 1
        elif not is_named and not has_modifier:
            priority = 2
        else:
            priority = 3

        return (priority, start_id)

    return sorted(buses, key=sort_key)


def preparing_bus_list(buses, name_start) -> str:
    """ Принимает список автобусов с дополнительными параметрами
    и названием остановки, автобусы с которой нужно поставить первыми.

    Готовит текст для одной строки ответа:
    автобусы через запятую с описанием (если нужно) для каждого.

    Возвращает текст ответа со списком автобусов (без времени)
    """
    text = ""
    buses = sort_buses(buses, name_start)  # Специальная сортировка автобусов
    # Разбираем имеющиеся автобусы на это время
    for bus_dict in buses:
        bus = bus_dict['bus']  # Автобус (str)
        bus_number = format_bus_number(bus.number)  # Буквы в кавычки
        modifiers = bus_dict.get('modifier', [])  # Модификатор ответа см. в документации
        add_text = ''

        # Модификатор есть, меняем ответ
        if modifiers:
            if "start_deff" in modifiers:
                # Название остановки отправления
                # не совпадает с изначально запрошенным
                add_text += f'От остановки {bus_dict["start"].name}. '
            if "both" in modifiers:
                # Один и тот же автобус может отправляться от
                # двух разных остановок с одинаковым названием
                if not add_text:
                    add_text += f'От остановки {bus_dict["start"].name}. '
                add_text += f'В сторону конечной {bus_dict["final_stop_finish"].name}. '
            if "finish_deff" in modifiers:
                # Hазвание остановки прибытия
                # не совпадает с изначально запрошенным
                add_text += f'На остановку {bus_dict["finish"].name}. '
            if "final_stop_one" in modifiers:
                # Идет через одну конечную остановку
                add_text += f'Через конечную {bus_dict["final_stop_finish"].name}. '
            if "final_stop_two" in modifiers:
                # Идет через две конечные остановки
                # В текущей реализации не используется
                add_text += (f'Через конечные {bus_dict["final_stop_finish"].name} '
                             f'и {bus_dict["final_stop_start"].name}. ')

        # Добавляем номер автобуса и модификатор в ответ
        add_text = f"({add_text})" if add_text else ''
        text += f'{bus_number} {add_text}\n'

    return text
