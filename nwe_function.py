"""
Функция нахождения маршрутов (объекты остановок отправления,
остановок прибытия, списки автобусов для каждой остановки прибытия).

Ввод:
- название остановки отправления
- название остановки прибытия

Вывод:
{
    остановка отправления 1 (объект): {
        остановка назначения 1 (объект): [список автобусов (объекты)],
        остановка назначения 2 (объект): [список автобусов (объекты)],
        ...
    },
    остановка отправления 2 (объект): {
        остановка назначения 1 (объект): [список автобусов (объекты)],
        остановка назначения 2 (объект): [список автобусов (объекты)],
        ...
    },
}

Алгоритм:
Остановки отправления и прибытия просчитываются вместе с группами,
куда они входят. Поэтому и тех и других может быть несколько.

1. Получаем список групп названий остановок из таблицы StopGroup,
   каждая группа это список названий остановок группы (итого получить список списков)
2. Создаем список start_list объектов остановок отправления. В него включаем все остановки
   из групп, в которой есть ее название и все остановок с таким названием (они должны быть первыми).
3. Создаем список finish_list объектов остановок прибытия, так-же как start_list
   в п.2.
4. Создаем контрольный сет check_router автобусов, для проверки
   и исключения уже имеющихся. Проверка не допустит попадания одного автобуса
   с разных остановок в группе.
5. Создаем основной словарь result, куда будем добавлять все остановки отправления
   с их содержимым.
6. Запускаем цикл по всем остановкам отправления for start in start_list.
   Названные пользователем остановки идут первыми, поэтому если будут повторяющиеся
   автобусы, они будут записаны только в эти остановки.
7. Создаем словарь all_finish, куда будем помещать остановки прибытия с их содержимым.
8. Запускаем цикл по всем остановкам прибытия for finish in finish_list
9. Создаем список buses_list, для записи автобусов прибывающих на текущую остановку.
10. Находим в таблице Order все автобусы (через Router), у которых в порядке
   следования остановок в маршруте, остановка start находится раньше
   остановки finish. Выбирая таким образом автобусы с нужным направлением.
11. Добавляем каждый найденный автобус в список buses_list и check_router.
   Если этот автобус отсутствовал до этого в check_router.
   Таким образом избегая повторений одного автобуса,
   если он проходит через разные остановки группы прибытия.
12. Добавляем список buses_list как значение ключа finish в all_finish,
   если список не пустой.
13. Завершение цикла finish_list. Переход к п.9.
14. Добавляем словарь all_finish как значение ключа start в result.
   Если словарь не пустой.
15. Завершение цикла start_list. Переход к п.7.
16. Возвращаем готовый словарь result.
"""
import json
from django.db.models import Subquery, OuterRef, F

# Предполагается, что модели находятся в app с названием 'schedule'
# Если это не так, исправьте импорты
from schedule.models import BusStop, StopGroup, Router, Order, Bus


def get_routers_by_two_busstop(start_stop_name: str, finish_stop_name: str) -> dict:
    """
    Находит маршруты между двумя остановками на основе предоставленного алгоритма.
    """
    # 1. Получаем список групп названий остановок
    stop_groups = [
        json.loads(group.list_name)
        for group in StopGroup.objects.all()
    ]

    def get_stops_with_groups(stop_name: str) -> list[BusStop]:
        """Вспомогательная функция для получения списка остановок с учетом групп."""
        # Остановки, точно совпадающие с названием
        primary_stops = list(BusStop.objects.filter(name=stop_name))
        
        grouped_stop_names = set()
        for group in stop_groups:
            if stop_name in group:
                for name in group:
                    grouped_stop_names.add(name)
        
        # Убираем уже найденные, чтобы не дублировать
        for stop in primary_stops:
            grouped_stop_names.discard(stop.name)

        grouped_stops = list(BusStop.objects.filter(name__in=list(grouped_stop_names)))
        
        # Возвращаем список, где названные пользователем остановки идут первыми
        return primary_stops + grouped_stops

    # 2. Создаем список start_list
    start_list = get_stops_with_groups(start_stop_name)

    # 3. Создаем список finish_list
    finish_list = get_stops_with_groups(finish_stop_name)

    # 4. Создаем контрольный сет check_router
    check_router = set()

    # 5. Создаем основной словарь result
    result = {}

    # 6. Запускаем цикл по всем остановкам отправления
    for start in start_list:
        # 7. Создаем словарь all_finish
        all_finish = {}

        # 8. Запускаем цикл по всем остановкам прибытия
        for finish in finish_list:
            # 9. Создаем список buses_list
            buses_list = []

            # 10. Находим автобусы с нужным направлением
            # Создаем подзапросы для получения порядковых номеров
            start_order_sq = Order.objects.filter(bus_stop=start, router=OuterRef('pk')).values('order_number')
            finish_order_sq = Order.objects.filter(bus_stop=finish, router=OuterRef('pk')).values('order_number')

            # Находим маршруты, где номер остановки start меньше номера finish
            valid_routers = Router.objects.annotate(
                start_order=Subquery(start_order_sq),
                finish_order=Subquery(finish_order_sq)
            ).filter(
                start_order__isnull=False,
                finish_order__isnull=False,
                start_order__lt=F('finish_order')
            )
            
            found_buses = [router.bus for router in valid_routers]

            # 11. Добавляем найденные автобусы в список
            for bus in found_buses:
                if bus not in check_router:
                    buses_list.append(bus)
                    check_router.add(bus)
            
            # 12. Добавляем непустой список автобусов в словарь
            if buses_list:
                all_finish[finish] = buses_list

        # 14. Добавляем непустой словарь в итоговый результат
        if all_finish:
            result[start] = all_finish
            
    # 16. Возвращаем готовый словарь
    return result
