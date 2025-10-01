from typing import Dict, List


class Filter:
    """
    Класс для накопления и фильтрации писка автобусов 
    с маршрутами после отбора маршрутов.
    """
    def __init__(self):
        """
        Определение словаря для хранения 
        объектов атвобусов-накопителей
        """
        self.bus_storage = {}

    class BusStorage:
        """
        Класс для сохранения марршрутов автобусов
        и фильтрации перед сохранением
        """
        def __init__(self):
            """
            Определение структур:
            storage -   словарь для сохранения маршрутов, по 1 на ключ {part: route}. 
                        part - часть маршрута (туда/назад), route - маршрут.
            best_priority - лучший приоритет маршрута для автобуса
            best_score - лучший балл маршрута для автобуса
            """
            self.storage = {}
            self.best_priority = 4  # Заведомо максимальное значение

        def save(self, route: Dict) -> bool:
            """
            Пробуем добавить полученный маршрут в 
            хранилище объекта автобуса-накопителя.

            Args:
                route - словарь с описанием маршрута

            Return:
                Возвращает результат добавления
            """
            priority = route["priority"]  # Приоритет маршрута
            score = route["score"]  # Баллы маршрута
            part = route["part"]  # Часть маршрута

            if self.best_priority < priority:
                # Сохраненные маршруты имеют больший приоритет они остаются
                return False

            if self.best_priority > priority:
                # Сохраненные маршруты имеют меньший приоритет, удаляем их
                self.storage = {}
                self.best_priority = priority  # Запоминаем лучший приоритет для автобуса

            # Приоритет больше или равен сохраненным
            saved_route = self.storage.setdefault(part, {})  # Получение или создание маршрута
            saved_score = saved_route.get("score", 10000)  # Получение сохраненных баллов
            if saved_score > score:
                # Новый маршрут лучше сохраненного (по лаллам)
                saved_route[part] = route  # Перезаписываем маршрут
                return True
            
            # Маршрут равен по приоритету 
            # и равен или меньше баллам (не сохраняем)
            return False
    
    def pair_filter(self, route: Dict) -> bool:
        """
        Получает или создает автобус-накопитель 
        и передает ему управление фильтрацией и записью
        """
        # Получение или создание объекта
        storage = self.bus_storage.setdefault(route["bus"], self.BusStorage())
        return storage.save(route)
    
    def get_bus_list(self) -> List[Dict]:
        """
        Формиироване списка маршрутов 
        с предварительной фильтрацией
        """
        # Находим лучший приоритет из всех автобусов
        best_priority = min([bus.best_priority for bus in self.bus_storage])

        result = []  # Список выдачи
        for bus in self.bus_storage:
            # Перебор объектов автобусов
            for _, route in bus.storage.items():
                # Проходим по частям маршрутов
                # и получаем маршруты
                if route["priority"] <= best_priority:
                    # Добавляе маршрут в список выдачи
                    result.append(route)
        
        return result
    