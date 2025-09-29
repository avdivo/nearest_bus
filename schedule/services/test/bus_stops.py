# Автобус №7
route1 = [{'bus_stop': '34519', 'bus_stop_name': 'Автобусный парк №2'}, {'bus_stop': '34413', 'bus_stop_name': 'Сыродельный комбинат'}, {'bus_stop': '34541', 'bus_stop_name': 'Майский посад'}, {'bus_stop': '5376', 'bus_stop_name': 'Городок'}, {'bus_stop': '5429', 'bus_stop_name': 'Школа № 2'}, {'bus_stop': '5537', 'bus_stop_name': 'Медицинский колледж'}, {'bus_stop': '5584', 'bus_stop_name': 'Рынок'}, {'bus_stop': '5553', 'bus_stop_name': 'Аптека № 80'}, {'bus_stop': '5451', 'bus_stop_name': 'Дом культуры'}, {'bus_stop': '5413', 'bus_stop_name': '1 Августа'}, {'bus_stop': '5533', 'bus_stop_name': 'Зелёная'}, {'bus_stop': '5587', 'bus_stop_name': 'Микрорайон Северный'}, {'bus_stop': '5424', 'bus_stop_name': 'Ивановского'}, {'bus_stop': '45065', 'bus_stop_name': 'Магистральная'}, {'bus_stop': '45069', 'bus_stop_name': 'Костёл Святого Антония'}, {'bus_stop': '45149', 'bus_stop_name': 'Школа № 11'}, {'bus_stop': '36856', 'bus_stop_name': 'Чехова'}, {'bus_stop': '5541', 'bus_stop_name': 'Микрорайон Северный'}, {'bus_stop': '5398', 'bus_stop_name': 'Борисовца'}, {'bus_stop': '5586', 'bus_stop_name': 'Зелёная'}, {'bus_stop': '5532', 'bus_stop_name': '1 Августа'}, {'bus_stop': '5503', 'bus_stop_name': 'Молодёжный центр'}, {'bus_stop': '5384', 'bus_stop_name': 'Дом культуры'}, {'bus_stop': '13779', 'bus_stop_name': 'Слуцкие Пояса'}, {'bus_stop': '13733', 'bus_stop_name': 'Проектный институт'}, {'bus_stop': '13753', 'bus_stop_name': 'Уреченская'}, {'bus_stop': '51629', 'bus_stop_name': 'Экологический центр'}, {'bus_stop': '51495', 'bus_stop_name': 'Дружная'}, {'bus_stop': '51506', 'bus_stop_name': 'Любанская'}, {'bus_stop': '51577', 'bus_stop_name': 'Микрорайон Новодворцы'}, {'bus_stop': '51539', 'bus_stop_name': 'РСУ'}, {'bus_stop': '51624', 'bus_stop_name': 'ССК'}]
route2 = [{'bus_stop': '51624', 'bus_stop_name': 'ССК'}, {'bus_stop': '51572', 'bus_stop_name': 'РСУ'}, {'bus_stop': '51658', 'bus_stop_name': 'Микрорайон Новодворцы'}, {'bus_stop': '51682', 'bus_stop_name': 'Любанская'}, {'bus_stop': '51632', 'bus_stop_name': 'Дружная'}, {'bus_stop': '51515', 'bus_stop_name': 'Экологический центр'}, {'bus_stop': '22815', 'bus_stop_name': 'Уреченская'}, {'bus_stop': '13616', 'bus_stop_name': 'Проектный институт'}, {'bus_stop': '13738', 'bus_stop_name': 'Типография'}, {'bus_stop': '5451', 'bus_stop_name': 'Дом культуры'}, {'bus_stop': '5413', 'bus_stop_name': '1 Августа'}, {'bus_stop': '5533', 'bus_stop_name': 'Зелёная'}, {'bus_stop': '5587', 'bus_stop_name': 'Микрорайон Северный'}, {'bus_stop': '36791', 'bus_stop_name': 'Чехова'}, {'bus_stop': '45071', 'bus_stop_name': 'Школа № 11'}, {'bus_stop': '61127', 'bus_stop_name': 'Кадетское училище'}, {'bus_stop': '54181', 'bus_stop_name': 'Магистральная'}, {'bus_stop': '5561', 'bus_stop_name': 'Ивановского'}, {'bus_stop': '5541', 'bus_stop_name': 'Микрорайон Северный'}, {'bus_stop': '5398', 'bus_stop_name': 'Борисовца'}, {'bus_stop': '5586', 'bus_stop_name': 'Зелёная'}, {'bus_stop': '5532', 'bus_stop_name': '1 Августа'}, {'bus_stop': '5503', 'bus_stop_name': 'Молодёжный центр'}, {'bus_stop': '5384', 'bus_stop_name': 'Дом культуры'}, {'bus_stop': '5513', 'bus_stop_name': 'Копыльская'}, {'bus_stop': '5596', 'bus_stop_name': 'Рынок'}, {'bus_stop': '5626', 'bus_stop_name': 'Медицинский колледж'}, {'bus_stop': '5562', 'bus_stop_name': 'Школа № 2'}, {'bus_stop': '34466', 'bus_stop_name': 'Городок'}, {'bus_stop': '34478', 'bus_stop_name': 'Майский посад'}, {'bus_stop': '34503', 'bus_stop_name': 'Сыродельный комбинат'}, {'bus_stop': '34519', 'bus_stop_name': 'Автобусный парк №2'}]

class BusStop:
    def __init__(self, bus_stop: str, bus_stop_name: str):
        """
        Создаем тестовые объекты остановок
        """
        self.id = bus_stop
        self.name = bus_stop_name

    def __str__(self):
        return f"{self.name} ({self.id})"

def prepare_route(route1=route1, route2=route2):
    """
    Подготовка списка списков маршрута
    """
    route_list = []
    for routers in [route1, route2]:
        chank = []
        for it in routers:
            id = it["bus_stop"]
            name = it["bus_stop_name"]
            chank.append(BusStop(id, name))
        route_list.append(chank)
    return route_list
