from typing import List, Any, Dict


class BestRoute:
    """
    Класс для хранения маршрута автобуса (последоватильностей остановок)
    и оценки маршрута по 2 остановкам.
    Находит варианты маршрутов от точки 1 к точке 2, 
    определяет направление в маршруте, приоритет и расстояние между точками.
    """
    def __init__(self, bus_router: List[List[Any]], start_name="", finish_name=""):
        """
        Подготавливает и сохрвняет маршрут, направления.
        Запоминает название остановок отправления и прибытия.
        
        Args:
            bus_router - список направлений в которых 
                         последовательности остановок
            start_name - название остановки отправления
            finish_name - название остановки прибытия
        """
        self.start_name = start_name
        self.finish_name = finish_name

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

    def find_all_distance_variants(self, start, finish) -> Dict:
        """
        Находит маршрут от остановки 1 к остановке 2. 
        Определяет для него приоритет и рассояние (между сотановками).
        Пересчитывает рассояние в баллы по принцыпу:
        если одна из остановок (отправления или прибытия) 
        имеет заданное название
        (главное, то, которое пользователь набрал в запросе)
        рассояние умножается на 100, если и вторая остановка 
        с заданным названием - на 200.

        Args:
            start - объект остановки отправления
            finish - объект остановки прибытия
            main_name - название остановки которую назвали
        Retutns:
            {
                "priority": приоритет,
                "score": баллы за маршрут,
                "direction": в какой части маршрута остановка отправления 1/2
            }
            При ошибках вернет пустой словарь.
        """
        # Множитель для вычисления баллов 1/100/200
        factor = 200
        transitions = {200: 100, 100: 1}
        if start.name == self.start_name:
            factor = transitions[factor]   
        if finish.name == self.finish_name:
            factor = transitions[factor]
        
        # Находим все позиции start и finish в общей последовательности
        positions1 = [i for i, val in enumerate(self.flat_sequence) if val == start]
        positions2 = [i for i, val in enumerate(self.flat_sequence) if val == finish]

        if not positions1 or not positions2:
            # Отсутствует одна или обе остановки   
            return {}

        # Словарь вывода
        result = {} 

        for pos1 in positions1:
            for pos2 in positions2:
                list1, _ = self.source_info[pos1]
                list2, _ = self.source_info[pos2]
                # --- Логика определения приоритетов ---
                # Случай 1: Остановки в одном и том же под-маршруте
                if list1 == list2:
                    # Приоритет 1: Прямой порядок (слева направо)
                    if pos1 < pos2:
                        priority = 1
                        score = (pos2 - pos1) * factor
                    # Приоритет 3: Обратный порядок (полный круг)
                    # Возможен только если есть несколько под-маршрутов
                    elif len(self.bus_router) > 1: # pos1 > pos2
                        priority = 3
                        score = ((self.total_length - pos1) + pos2) * factor
                    else:
                        return {}
                # Случай 2: Остановки в разных под-маршрутах
                else: # list1 != list2
                    # Приоритет 2: Переход между маршрутами
                    distance = pos2 - pos1 if pos1 < pos2 else (self.total_length - pos1) + pos2
                    priority = 2
                    score = distance * factor

                direction = list1 + 1
                # print (f"priority: {priority}, score: {score}, direction: {direction}" )
                # Фильтр маршрутов
                if not result or (result["priority"] >= priority and result["score"] > score):
                    result["priority"] = priority
                    result["score"] = score
                    result["direction"] = direction

        return result
