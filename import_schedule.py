from selenium import webdriver
from selenium.webdriver.common.by import By
import re, os, json
from time import sleep
from datetime import time


def save_result(result: dict):
    """Сохраняет результат в файл."""
    with open('result.json', "w") as file:
        json.dump(result, file, ensure_ascii=False, indent=4)


def final_station(string):
    """Создает списки конечных остановок и Направлений.
    Принимает список направлений (через тире), создает список из названий отделенных тире.
    Каждый раз сохраняет списки.
    """
    data_final = []
    file_final = 'final.json'
    if os.path.exists(file_final):
        with open(file_final, "r") as file:
            data_final = json.load(file)
    data_direction = []
    file_direction = 'direction.json'
    if os.path.exists(file_direction):
        with open(file_direction, "r") as file:
            data_direction = json.load(file)

    bs_list = []
    dir_list = []
    for s in string:
        if not s:
            continue
        dir_list.append(s)
        for bs in s.split(' - '):
            out = bs.strip()
            if out:
                bs_list.append(out)

    data = set(data_final).union(set(bs_list))
    with open(file_final, "w") as file:
        json.dump(list(data), file, ensure_ascii=False, indent=4)
    data = set(data_direction).union(set(dir_list))
    with open(file_direction, "w") as file:
        json.dump(list(data), file, ensure_ascii=False, indent=4)


def get_schedule():
    """Получение расписания.
    Возвращает список с текстовым расписанием"""
    table = driver.find_elements(By.XPATH, '//*[@id="schedule"]')  # Чтение таблицы
    hours, minits = 0, 0
    schedule = []

    # Значения времени разделены переносами строки и пробелами
    # В первой строке заголовки. Часы записаны с двоеточием
    # После часов идут значения минут (одно или несколько, для этого часа)
    try:
        strings = table[0].text.split()  # Разделяем на цифры по пробелам и переносам
    except:
        print("Не удалось распознать таблицу.")
        return {}

    for string in strings:
        number = re.findall(r'\d+', string)  # Получаем из строки число, если оно там есть
        if not number:  # Если числа нет - пропускаем
            continue
        if ':' in string:
            hours = number[0]  # Если в строке есть двоеточие - то это значение часов
        else:
            # Если просто число - это минуты
            schedule.append(f'{hours}:{number[0]}')  # Добавляем время
    return schedule


def get_days_and_time():
    # return {}
    """Получаем дни недели и расписание на эти дни.
    Возвращает словарь: {день недели: [расписание],...} для всех дней недели."""
    box = None
    while not box:
        # Дождаться отображения списка дней
        box = driver.find_elements(By.XPATH, f'/html/body/div[2]/div/div[2]/div[4]/div/div[2]/div[2]/div[1]')
    days = box[0].find_elements(By.TAG_NAME, "button")  # Получить кнопки дней

    # Нажать каждую кнопку пн, вт...
    res = dict()
    for day in days:
        day.click()
        sleep(0.3)
        res[day.text] = get_schedule()  # Получаем расписание

    return res

def get_direction_and_bus_stop():
    """Получаем направления движения (маршруты) и Списка остановок.
    Возвращает словарь: {
                            маршрут (конечные через тире): {
                                остановка название: {
                                    'id': идентификатор,
                                    'schedule': {расписание по дням}
                                },
                                ...
                            },
                            ...
                        }
    """
    res = dict()  # Возвращаемый словарь
    # Направления
    directions = []
    for i in range(5):
        directions2 = driver.find_elements(By.XPATH, f'/html/body/div[2]/div/div[2]/div[4]/div/div[2]/h4[{i}]')
        if directions2:
            directions.append(directions2[0].text)
    # return directions

    # Списки остановок
    string = 'ABCDEF'
    for i, direction in enumerate(directions):
        # Полный список остановок на маршруте
        bus_stops = len(driver.find_elements(By.XPATH, f'//*[@id="trip{string[i]}"]/a[*]')) + 1
        bus_stop_i = 1
        # Перебираем остановки кликаем на каждой для открытия расписания
        out = dict()  # Часть возвращаемого словаря
        while bus_stops - bus_stop_i:
            bus_stop = driver.find_elements(By.XPATH, f'//*[@id="trip{string[i]}"]/a[{bus_stop_i}]')
            bus_stop_name = bus_stop[0].text
            # print('   ', bus_stop[0].text, bus_stop_id)
            bus_stop[0].click()
            sleep(1)
            bus_stop_id = driver.current_url.split('/')[-2]  # Уникальный номер остановки (id)
            get = get_days_and_time()  # Вызов функции получения расписаний
            bus_stop_i += 1
            out[bus_stop_name] = {'id': bus_stop_id, 'schedule': get}

        res[direction] = out  # Заполняем данные для возврата

    return res

# Запускаем браузер
driver = webdriver.Chrome()

# Открываем сайт
url = "https://gpmopt.by/mopt/Home/Index/sluck#/routes/bus"
driver.get(url)
sleep(2)

# Получаем содержимое страницы
page_source = driver.page_source

# Находим номера маршрутов (номера автобусов) и записываем их в список
direction_len = len(driver.find_elements(By.XPATH, '//*[@id="routeList"]/li[*]/a'))
i = 0
result = dict()  # Словарь с результатами работы
while direction_len - i:
    # Читаем найденные автобусы, получаем их номера.
    # Кликаем поочереди даля открытия маршрутов автобуса
    directions = driver.find_elements(By.XPATH, '//*[@id="routeList"]/li[*]/a')
    bus_number = directions[i].text.split()[0]
    if bus_number == '201С' or bus_number == '201C':
        # Это останавливает процесс, чтобы не сканировать пригородные маршруты
        break
    # print('\nАвтобус', bus_number)
    directions[i].click()
    sleep(2)

    result[bus_number] = get_direction_and_bus_stop()  # Функция читает маршруты

    # final_station(d)  # Функция создает список конечных остановок
    driver.get(url)  # Возврат к начальной странице и переход к следующему номеру
    sleep(1)
    i += 1
    print(result)
    save_result(result)  # Сохранение результата

print(result)
