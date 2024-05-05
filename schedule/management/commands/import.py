"""Команда заполняет БД данными с сайта
Миноблавтотранс https://gpmopt.by/mopt/Home/Index/sluck#/routes/bus.
Расписание подготавливается парсером сайта в файле import_schedule.py на локальной машине
и сохраняется в файле result.json.
Формат файла:
{
    номер автобуса: {
        маршрут (конечные через тире): {
            остановка название: {
                'id': идентификатор,
                'schedule': {
                        день недели ("пн", "вт"...): [время (17:15, 18:25...)],
                        ...
                }
            },
            ...
        },
        ...
    }
}
Этот файл должен находиться в корне проекта для выполнения этой команды.
"""
import os
import json

from schedule.services.add_to_models import (add_bus, add_bus_stop, add_final_stop_to_bus_stop,
                                             add_router, add_final_stop_to_bus, add_order, add_time_point)


# Получение данных из файла
try:
    file_final = 'result.json'
    if os.path.exists(file_final):
        with open(file_final, "r") as file:
            data = json.load(file)
    else:
        print('Отсутствует файл с расписанием Миноблавтотранс.')
except:
    print('Ошибка импорта файла с  расписанием Миноблавтотранс.')

# Обработка данных и заполнение БД


for bus, directions in data.items():  # Номер автобуса и названия маршрутов
    print(bus)
    bus_obj = add_bus(bus)  # Добавление автобуса в БД +++++++++++++++++++
    for direction, bus_stops in directions.items():  # Название маршрута и список остановок на нем
        if not direction:
            # Защита от пустого маршрута (в списке попадается)
            continue
        print('    ', direction)
        bus_stop_start, bus_stop_end = direction.split(' - ')  # Начало и конец маршрута
        # Проверяем, являются ли первая и последняя остановки в списке конечными
        # записанными в названии маршрута. Сохраняем их в БД как конечные.
        try:
            id = bus_stops[bus_stop_start]['id']  # id остановки
            # Добавление конечной остановки в БД +++++++++++++++++++
            bus_stop_start_obj = add_bus_stop(bus_stop_start, id, True)
            id = bus_stops[bus_stop_end]['id']  # id остановки
            # Добавление конечной остановки в БД +++++++++++++++++++
            bus_stop_end_obj = add_bus_stop(bus_stop_end, id, True)
        except:
            raise
            exit(f'Конечные остановки Автобуса {bus} в маршруте {direction} не найдены в списке.')

        # Добавление конечных к автобусу +++++++++++++++++++
        add_final_stop_to_bus(bus_obj, [bus_stop_start_obj, bus_stop_end_obj])
        # Добавляем маршрут +++++++++++++++++++
        router_obj = add_router(bus_stop_start_obj, bus_stop_end_obj, bus_obj)

        for bus_stop, rest in bus_stops.items():  # Остановка и остальные данные (в т.ч. расписание)

            external_id = rest['id']  # id остановок по Миноблавтотранс
            schedules = rest['schedule']  # Списки расписаний по дням недели

            bus_stop_obj = add_bus_stop(bus_stop, external_id)  # Добавляем остановку в БД +++++++++++++++++++
            # Добавление конечной на которую можно попасть с этой остановки +++++++++++++++++++
            add_final_stop_to_bus_stop(bus_stop_obj, bus_stop_end_obj, 'to')
            # Добавление конечной с которой можно попасть на эту остановку +++++++++++++++++++
            add_final_stop_to_bus_stop(bus_stop_obj, bus_stop_start_obj, 'from')

            # Добавление номера следования остановки в маршруте +++++++++++++++++++
            add_order(router_obj, bus_stop_obj)

            for day, times in schedules.items():  # Разбираем расписания по дням недели
                for time in times:  # Разбираем список с временными метками в виде строк
                    add_time_point(day, time, bus_obj, bus_stop_obj)

exit()