"""Команда заполняет БД данными с сайта
Миноблавтотранс https://gpmopt.by/mopt/Home/Index/sluck#/routes/bus.
Расписание подготавливается парсером сайта в файле import_schedule.py на локальной машине
и сохраняется в файле result1.json.
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
При экспорте данных меняется id остановок в функции merge_bus_stops.
"""
import os
import json

from schedule.services.add_to_models import (add_bus, add_bus_stop, add_final_stop_to_bus_stop,
                                             add_router, add_final_stop_to_bus, add_order,
                                             add_time_point, clear_all_tables)

# # Может потребоваться одно название, см. функцию add_bus_stop из модуля add_to_models
# IDS = {'5629': ['5608', '5629']}  #'64730':['5461', '64730']}  закомментировал по причине что для 6 на Автовокзале ставилось расписание остановки в обратную сторону.
# def merge_bus_stops(id):
#     """Функция для объединения двух остановок в одну.
#     Нужна в случае 2 остановок с одним именем на одной стороне,
#     но ведущих по разным направлениям. Когда их можно признать одной остановкой.
#
#     Пример и случай для которого создана это остановка Молодежный центр.
#     Одна находится на улице Ленина (id 5608), другая на улице Социалистической (id 5629).
#     В обоих случаях присвоим id 5629.
#     """
#     for key, value in IDS.items():
#         if id in value:
#             return key
#     return id


clear_all_tables()  # Очистка всех таблиц БД (перед импортом новых данных)

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
        try:
            bus_stop_start = next(iter(bus_stops))
            bus_stop_end = next(reversed(bus_stops))
            id = bus_stops[bus_stop_start]  # id остановки
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

        for i, (bus_stop_with_key, rest) in enumerate(bus_stops.items()):  # Остановка и остальные данные (в т.ч. расписание)

            bus_stop_name = bus_stop_with_key.split('|')[0]

            external_id = rest['id']  # id остановок по Миноблавтотранс
            schedules = rest['schedule']  # Списки расписаний по дням недели

            bus_stop_obj = add_bus_stop(bus_stop_name, external_id)  # Добавляем остановку в БД +++++++++++++++++++
            # Добавление конечной на которую можно попасть с этой остановки +++++++++++++++++++
            add_final_stop_to_bus_stop(bus_stop_obj, bus_stop_end_obj, 'to')
            # Добавление конечной с которой можно попасть на эту остановку +++++++++++++++++++
            add_final_stop_to_bus_stop(bus_stop_obj, bus_stop_start_obj, 'from')

            # Добавление номера следования остановки в маршруте +++++++++++++++++++
            add_order(router_obj, bus_stop_obj)

            if i == len(bus_stops) - 1:
                # Если это последняя остановка в маршруте, ее расписание записывать не нужно
                # там время прибытия на остановку.
                continue
            for day, times in schedules.items():  # Разбираем расписания по дням недели
                for time in times:  # Разбираем список с временными метками в виде строк
                    add_time_point(day, time, bus_obj, bus_stop_obj)

exit()
