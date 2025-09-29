from typing import List, Any, Dict
from bus_stops import prepare_route

# Маршрут. Номера остановок
# bus_router = [[1,2,3,4,5,6,7,8,9,10]]
# bus_router = [[1,2,3,4,5], [3,4,5]]
# bus_router = [[1,2,3,4,5], [1,2,3,4,5]]
bus_router = prepare_route()
# print(bus_router)
start_list = [2,3]  # Остановки отправления
finish_list = [7,8]  # Остановки прибытия

start = bus_router[0][16]  # Остановка отправления
finish = bus_router[1][14]  # Остановка прибытия
# Названия остановок (те, что назвал пользователь)
main_name1 = ""
main_name2 = ""



class RouterCalc:
    """
    Класс для хранения маршрута автобуса (последоватильностей остановок)
    и оценки маршрута по 2 остановкам.
    Находит варианты маршрутов от точки 1 к точке 2, 
    определяет направление в маршруте, приоритет и расстояние между точками.
    """
    def __init__(self, bus_router: List[List[Any]]):
        """
        Подготавливает и сохрвняет маршрут и направления

        Args:
            bus_router - список направлений в которых 
                         последовательности остановок
        """
        self.bus_router = bus_router
        # Создаем плоский список всех остановок для упрощения поиска
        self.flat_sequence = []  # значения
        # Сохраняем информацию об исходном списке и индексе для каждой остановки
        self.source_info = []    # (list_index, inner_index)

        for list_idx, lst in enumerate(bus_router):
            for inner_idx, value in enumerate(lst):
                self.flat_sequence.append(value)
                self.source_info.append((list_idx, inner_idx))

        self.total_length = len(self.flat_sequence)

    def find_all_distance_variants(self, point1, point2, main_name1="", main_name2="") -> List[Dict]:
        """
        Находит маршрут от остановки 1 к остановке 2. 
        Определяет для него приоритет, рассояние (между сотановками).
        Пересчитывает рассояние в баллы по принцыпу:
        если одна из остановок (отправления или прибытия) 
        имеет заданное название
        (главное, то, которое пользователь набрал в запросе)
        рассояние умножается на 100, если и вторая остановка 
        с заданным названием - на 200.

        Args:
            point1 - объект остановки отправления
            point2 - объект остановки прибытия
            main_name - название остановки которую назвали
        Retutns:
            [{
                "direction": в какой части маршрута остановка отправления 1/2, 
                "priority": приоритет,
                "score": баллы за маршрут
            }]
            При ошибках вернет пустой список.
        """
        # Множитель для вычисления баллов 1/100/200
        factor = 200
        transitions = {200: 100, 100: 1}
        if point1.name == main_name1:
            factor = transitions[factor]   
        if point2.name == main_name2:
            factor = transitions[factor]
        
        # Находим все позиции point1 и point2 в общей последовательности
        positions1 = [i for i, val in enumerate(self.flat_sequence) if val == point1]
        positions2 = [i for i, val in enumerate(self.flat_sequence) if val == point2]

        if not positions1 or not positions2:
            # Отсутствует одна или обе остановки   
            return []

        # Список вывода
        result = []

        for pos1 in positions1:
            for pos2 in positions2:
                list1, _ = self.source_info[pos1]
                list2, _ = self.source_info[pos2]
                
                item = None
                # --- Логика определения приоритетов ---
                # Случай 1: Остановки в одном и том же под-маршруте
                if list1 == list2:
                    # Приоритет 1: Прямой порядок (слева направо)
                    if pos1 < pos2:
                        item = {"priority": 1, "score": (pos2 - pos1) * factor}
                    # Приоритет 3: Обратный порядок (полный круг)
                    # Возможен только если есть несколько под-маршрутов
                    elif len(self.bus_router) > 1: # pos1 > pos2
                        item = {"priority": 3, "score": ((self.total_length - pos1) + pos2) * factor}
                # Случай 2: Остановки в разных под-маршрутах
                else: # list1 != list2
                    # Приоритет 2: Переход между маршрутами
                    distance = pos2 - pos1 if pos1 < pos2 else (self.total_length - pos1) + pos2
                    item = {"priority": 2, "score": distance * factor}

                if item:
                    item['direction'] = list1 + 1
                    result.append(item)

        return result
    

obj = RouterCalc(bus_router=bus_router)

result = obj.find_all_distance_variants(start, finish, main_name1, main_name2)

print()
print(start,"-", finish)
for res in result:
    print(res)
print()
