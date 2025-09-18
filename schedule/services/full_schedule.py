import datetime
from typing import Dict, List, Tuple
from functools import cmp_to_key

from schedule.models import BusStop, Bus, Schedule, Router
from schedule.services.timestamp import time_generator
from tbot.services.functions import date_now
from utils.sorted_buses import compare_name


def full_schedule(bus_stop_name: str, day_of_week: int = None) -> Dict[Bus, Dict[str, List[datetime.time]]]:
    """
    Формирует полное расписание для всех одноименных остановок на текущий день.
    Алгоритм schedule/services/full_schedule.py.

    Эта функция выполняет следующие шаги:
    1. Находит все остановки с заданным именем (`bus_stop_name`).
    2. Получает все записи о времени (`Schedule`) для найденных остановок на этот день.
    3. Группирует время по автобусам, а затем по их маршрутам. Маршрут определяется
       для каждой пары (автобус, остановка).
    4. Возвращает отсортированный словарь, где ключи - объекты автобусов (`Bus`),
       а значения - словари, в которых ключи - маршруты (объекты),
       а значения - отсортированные списки времени отправления (`datetime.time`).

    Args:
        bus_stop_name (str): Название автобусной остановки для поиска.
        day_of_week (Optional[int]): День недели (1-7) или None для автоопределения.

    Returns:
        Dict[Bus, Dict[str, List[datetime.time]]]: Словарь с полным расписанием,
        отсортированный по номерам автобусов. Если остановки не найдены,
        возвращается пустой словарь.
        Пример:
        {
            <Bus: Автобус №3>: {
                <Router: Автобус №3 Мясокомбинат - Социалистическая>: [datetime.time(7, 15), ...]
                <Router: Автобус №3 Социалистическая - Мясокомбинат>: [datetime.time(6, 30), ...],
            },
            ...
        }
    """
    # 1. Найти объекты всех одноименных остановок отправления.
    # Выполняем запрос к БД для получения всех остановок с указанным именем.
    bus_stops = BusStop.objects.filter(name=bus_stop_name)
    if not bus_stops.exists():
        # Если ни одной остановки не найдено, возвращаем пустой словарь.
        return {}

    # Получаем все записи времени отправления для найденных остановок в нужный день.
    schedules = Schedule.objects.filter(
        bus_stop__in=bus_stops,
        day=day_of_week
    ).select_related('bus', 'bus_stop').order_by('time')

    # Собираем промежуточный словарь по автобусам и их остановкам.
    # { автобус: { остановка: [список временных меток] } }
    intermediate_schedule: Dict[Bus, Dict[BusStop, List[datetime.time]]] = {}
    for schedule in schedules:
        # .setdefault() создает ключ с пустым словарем/списком, если его нет.
        bus_schedules = intermediate_schedule.setdefault(schedule.bus, {})
        stop_schedules = bus_schedules.setdefault(schedule.bus_stop, [])
        stop_schedules.append(schedule.time)
    
    # for im in intermediate_schedule.items():
    #     print(im)

    # Ставим вре временные метки для каждой остановки.
    for bus, bus_schedules in intermediate_schedule.items():
        for stop, times in bus_schedules.items():
            bus_schedules[stop] = list(time_generator(times, datetime.time(3, 0), 1440))

    # for im in intermediate_schedule.items():
    #     print(im)

    # 2. Преобразование: меняем в исходном словаре остановки на маршруты.
    final_schedule: Dict[Bus, Dict[Tuple[Router], List[datetime.time]]] = {}
    for bus, stop_schedules in intermediate_schedule.items():
        final_schedule.setdefault(bus, {})
        mark = 0
        for stop, times in stop_schedules.items():
            try:
                # Для каждой пары (автобус, остановка) получаем соответствующий маршрут.
                # Используем .get(), чтобы обработать случаи, когда маршрут не найден или их несколько.
                # Ожидается, что для конкретного автобуса остановка встречается только на одном маршруте.
                routers = Router.objects.filter(bus=bus, orders_for_router__bus_stop=stop)
                router_list = tuple(routers) + (mark,)  # Добавляем метку для уникальности ключа
                final_schedule[bus][tuple(router_list)] = times
                mark += 1
            except Router.DoesNotExist:
                # Эта ситуация может возникнуть при несогласованности данных в БД.
                # Например, есть расписание для остановки, но она не привязана к маршруту.
                # Просто пропускаем такую запись, можно добавить логирование.
                print(f"Warning: Маршрут не найден для автобуса {bus} и остановки {stop}.")

    # 3. Сортируем итоговый словарь по номерам автобусов для упорядоченного вывода.
    # Используем кастомную функцию сортировки `compare_name` для корректной обработки номеров типа "10а".
    sorted_buses = sorted(
        final_schedule.keys(),
        key=cmp_to_key(lambda bus1, bus2: compare_name(bus1.number, bus2.number))
    )

    # Собираем финальный отсортированный словарь в нужном порядке.
    sorted_final_schedule = {bus: final_schedule[bus] for bus in sorted_buses}

    return sorted_final_schedule
