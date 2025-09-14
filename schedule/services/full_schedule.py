import os
import sys
import django

import datetime
from typing import Dict, List
from functools import cmp_to_key

from utils.sorted_buses import compare_name
from schedule.models import BusStop, Bus, Schedule


def full_schedule(bus_stop: BusStop) -> Dict[Bus, List[datetime.time]]:
    """
    Подготовка данных для полного расписания по одной остановке.

    Эта функция принимает объект автобусной остановки и возвращает словарь,
    где ключами являются объекты автобусов (Bus), а значениями - отсортированные
    списки времени (datetime.time), когда эти автобусы прибывают на данную остановку.

    Args:
        bus_stop (BusStop): Объект автобусной остановки, для которой нужно получить расписание.

    Returns:
        Dict[Bus, List[datetime.time]]: Словарь с расписанием, отсортированный по номерам автобусов.

    """
    # Создаем пустой словарь для хранения расписания.
    schedule_data: Dict[Bus, List[datetime.time]] = {}
    # Выполняем запрос к базе данных для получения всех записей расписания для данной остановки.
    schedules = Schedule.objects.filter(bus_stop=bus_stop).select_related('bus')
    # Обрабатываем результаты запроса.
    for schedule in schedules:
        schedule_data.setdefault(schedule.bus, []).append(schedule.time)
    # Сортируем списки времен для каждого автобуса.
    for times in schedule_data.values():
        times.sort()
    # Получаем список объектов Bus из ключей словаря.
    buses = list(schedule_data.keys())
    # Сортируем автобусы, используя специальную функцию compare_name.
    sorted_bus_objects = sorted(
        buses,
        key=cmp_to_key(lambda bus1, bus2: compare_name(bus1.number, bus2.number))
    )
    # Создаем финальный отсортированный словарь.
    final_schedule = {bus: schedule_data[bus] for bus in sorted_bus_objects}
    return final_schedule
