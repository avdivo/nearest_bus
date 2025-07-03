# Функции добавления данных в БД
from datetime import datetime

from schedule.models import BusStop, Bus, Router, Order, Schedule

from utils.translation import get_day_number


def add_bus(number: str, station: BusStop = None, active=None):
    """Добавление или изменение автобуса.
    Принимает Номер, останову (объект), Активность.
    Обновится активность (ходит ли автобус), если она специально передана.
    Если нет автобус добавится, остановка добавится или не изменится.
    Возвращает объект.
    """
    defaults = dict()
    if active is not None:
        defaults['active'] = active
    bus = Bus.objects.update_or_create(number=number, defaults=defaults)
    if station:
        bus[0].station.add(station)
    return bus[0]


def add_final_stop_to_bus(bus: Bus, stations: list):
    """Добавление конечных остановок к автобусу.
    Каждая автобус имеет список конечных, на которых он начинает и заканчивает движение.
    Этот список пополняет эта функция.
    Принимает Автобус и список конечных остановок.
    """
    for station in stations:
        add_bus(bus.number, station)


def add_bus_stop(name: str, external_id: str, finish: bool = False):
    """Добавление автобусной остановки.
    Принимает Название, id, Конечная ли она - по умолчанию не конечная.
    Значение конечности может поменяться только на True. В другом случае оно не исправляется.
    Добавляет остановку, если ее еще нет (с таким id) или обновляет.
    Возвращает объект.
    """
    # Даем одно название 2 остановкам (это когда объединяем остановки
    # Например Автовокзал и Автовокзал *
    # Остановки объединяются так-же по id в функции merge_bus_stops из модуля import
    # names = {'Автовокзал': ['Автовокзал', 'Автовокзал *']}
    # for n in names.keys():
    #     if name in names[n]:
    #         name = n
    # закомментировал по причине что для 6 на Автовокзале ставилось расписание остановки в обратную сторону.

    # Переименовал остановку для ясности
    names = {'Автовокзал (кольцо)': ['Автовокзал *']}
    for n in names.keys():
        if name in names[n]:
            name = n

    defaults = {'name': name}
    if finish:
        defaults['finish'] = finish
    return BusStop.objects.update_or_create(external_id=external_id, defaults=defaults)[0]


def add_final_stop_to_bus_stop(bus_stop: BusStop, station: BusStop, direction: str):
    """Добавление конечных остановок к остановкам.
    Каждая остановка имеет список конечных, к которым она ведет.
    И список конечных, которые ведут к ней.
    Эти списки пополняет эта функция.
    Принимает Остановку, конечную остановку и направление в виде строки:
    to - к каким конечным, from - от каких конечных.
    """
    if direction == 'to':
        bus_stop.con_to.add(station)
    else:
        bus_stop.con_from.add(station)


def add_router(start: BusStop, end: BusStop, bus: Bus):
    """Добавление маршрута.
    Принимает Остановку начала маршрута, Остановку конца маршрута и Автобус.
    Возвращает объект.
    """
    return Router.objects.create(start=start, end=end, bus=bus)


def add_order(router: Router, bus_stop: BusStop):
    """Добавление порядка остановок в маршруте.
    Принимает маршрут, остановку.
    Сама добавляет порядковый номер, в зависимости от порядка создания объектов.
    Возвращает объект.
    """
    return Order.objects.create(router=router, bus_stop=bus_stop)


def add_time_point(day: str, time: str, bus: Bus, bus_stop: BusStop):
    """Добавление временной метки в таблицу.
    Таблица хранит День недели (1-7), Временную метку, Автобус и Остановку.
    Принимает Сокращенное название дня недели, Временную метку (строкой),
    Автобус, Остановку.
    """
    Schedule.objects.create(day=get_day_number(day), time=datetime.strptime(time, "%H:%M").time(),
             bus=bus, bus_stop=bus_stop)


def clear_all_tables():
    """Очистка всех таблиц расписания автобусов в БД."""
    # Сначала удаляем объекты из таблиц, которые не имеют внешних ссылок
    Schedule.objects.all().delete()
    Order.objects.all().delete()
    # Затем удаляем объекты из таблиц, которые могут иметь внешние ссылки
    Router.objects.all().delete()
    Bus.objects.all().delete()
    BusStop.objects.all().delete()

    print('Все таблицы расписания автобусов очищены.')
