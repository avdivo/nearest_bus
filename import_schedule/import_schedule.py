import logging
import hashlib
import colorlog
import re, os, json
from time import sleep, time
from functools import cmp_to_key
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .buses_list import buses
from utils.sorted_buses import sorted_buses, compare_name

# Определяем цветовую схему для разных уровней логов
log_colors = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

# Создаем обработчик с цветами для консоли
handler = colorlog.StreamHandler()
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(message)s",  # Оставляем только само сообщение
    log_colors=log_colors
)
handler.setFormatter(formatter)

# Настройка базового логгера с использованием цветного обработчика
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.handlers = [handler]  # Заменяем обработчики, чтобы избежать дублирования


# def final_station(string):
#     """Создает списки конечных остановок и Направлений.
#     Принимает список направлений (через тире), создает список из названий отделенных тире.
#     Каждый раз сохраняет списки.
#     """
#     data_final = []
#     file_final = 'final.json'
#     if os.path.exists(file_final):
#         with open(file_final, "r") as file:
#             data_final = json.load(file)
#     data_direction = []
#     file_direction = 'direction.json'
#     if os.path.exists(file_direction):
#         with open(file_direction, "r") as file:
#             data_direction = json.load(file)
#
#     bs_list = []
#     dir_list = []
#     for s in string:
#         if not s:
#             continue
#         dir_list.append(s)
#         for bs in s.split(' - '):
#             out = bs.strip()
#             if out:
#                 bs_list.append(out)
#
#     data = set(data_final).union(set(bs_list))
#     with open(file_final, "w") as file:
#         json.dump(list(data), file, ensure_ascii=False, indent=4)
#     data = set(data_direction).union(set(dir_list))
#     with open(file_direction, "w") as file:
#         json.dump(list(data), file, ensure_ascii=False, indent=4)


def get_schedule(driver):
    """Получение расписания.
    Возвращает список с текстовым расписанием"""

    table = WebDriverWait(driver, 10).until(
        EC.visibility_of_all_elements_located((By.XPATH, '//*[@id="schedule"]'))
    )
    hours, minits = 0, 0
    schedule = []

    # Значения времени разделены переносами строки и пробелами
    # В первой строке заголовки. Часы записаны с двоеточием
    # После часов идут значения минут (одно или несколько, для этого часа)
    try:
        strings = table[0].text.split()  # Разделяем на цифры по пробелам и переносам
    except:
        logger.error(f"Не удалось распознать таблицу.")
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


def get_days_and_time(driver):
    """Получаем дни недели и расписание на эти дни.
    Возвращает словарь: {день недели: [расписание],...} для всех дней недели."""
    box = None
    # sleep(0.1)
    while not box:
        # Дождаться отображения списка дней
        box = driver.find_elements(By.XPATH, f'/html/body/div[2]/div/div[2]/div[4]/div/div[2]/div[2]/div[1]')
    days = box[0].find_elements(By.TAG_NAME, "button")  # Получить кнопки дней

    # Нажать каждую кнопку пн, вт...
    res = dict()
    for day in days:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(day))
        day_text = day.text
        if "disabled" not in day.get_attribute("class"):
            day.click()
            res[day_text] = get_schedule(driver)  # Получаем расписание
        else:
            res[day_text] = []
    return res


def get_direction_and_bus_stop(driver):
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

    wait = WebDriverWait(driver, 10)
    result = {}
    for i in range(99):  # Большое число — чтобы пройти по всем секциям, пока не появится исключение
        try:
            # Ждем контейнер и извлекаем текущий заголовок и соответствующий блок ссылок
            container = wait.until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div[2]/div[4]/div")))
            headings = container.find_elements(By.TAG_NAME, "h4")
            list_groups = container.find_elements(By.CLASS_NAME, "list-group")

            heading = headings[i].text.strip()  # Маршрут
            group = list_groups[i]
            # print(f"\n🔸 Секция: {heading}")

            # Получаем все ссылки <a> внутри этой секции
            links = group.find_elements(By.TAG_NAME, "a")
            result[heading] = {}

            for j in range(len(links)):
                # После возврата нужно пересобрать DOM и найти ту же ссылку заново
                container = wait.until(
                    EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div[2]/div[4]/div")))
                group = container.find_elements(By.CLASS_NAME, "list-group")[i]
                links = group.find_elements(By.TAG_NAME, "a")
                h6 = links[j].find_element(By.TAG_NAME, "h6")
                name = h6.text.strip()
                result[heading][name] = {}

                # print(f"  🔹 Переход к: {name}")
                links[j].click()
                bus_stop_id = driver.current_url.split('/')[-2]  # Уникальный номер остановки (id)
                get = get_days_and_time(driver)  # Вызов функции получения расписаний
                result[heading][name]["id"] = bus_stop_id
                result[heading][name]["schedule"] = get
                driver.back()

        except IndexError:
            break  # Когда секции закончились

    return result

    # # Списки остановок
    # string = 'ABCDEF'
    # for i, direction in enumerate(directions):
    #     # logger.info(f"Маршрут {direction}")
    #     # Полный список остановок на маршруте
    #     bus_stops = len(driver.find_elements(By.XPATH, f'//*[@id="trip{string[i]}"]/a[*]')) + 1
    #     bus_stop_i = 1
    #     # Перебираем остановки кликаем на каждой для открытия расписания
    #     out = dict()  # Часть возвращаемого словаря
    #     while bus_stops - bus_stop_i:
    #         repeat = False
    #         while not repeat:
    #             try:
    #                 bus_stop = driver.find_elements(By.XPATH, f'//*[@id="trip{string[i]}"]/a[{bus_stop_i}]')
    #                 bus_stop_name = bus_stop[0].text
    #
    #                 # Перемотка к нужному элементу
    #                 driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", bus_stop[0])
    #
    #                 # Ожидание элемента
    #                 WebDriverWait(driver, 5).until(EC.element_to_be_clickable(bus_stop[0]))
    #                 bus_stop[0].click()
    #                 # sleep(0.2)
    #                 bus_stop_id = driver.current_url.split('/')[-2]  # Уникальный номер остановки (id)
    #                 get = get_days_and_time(driver)  # Вызов функции получения расписаний
    #                 repeat = True
    #             except Exception as e:
    #                 logger.warning(f"Ошибка. Повтор.")
    #                 repeat = False
    #
    #         bus_stop_i += 1
    #         out[bus_stop_name] = {'id': bus_stop_id, 'schedule': get}
    #
    #     res[direction] = out  # Заполняем данные для возврата
    #
    # return res


def calculate_md5_from_dict(data: dict) -> str:
    """Получение хэша md5 из словаря"""
    json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.md5(json_str.encode('utf-8')).hexdigest()


def save_bus(schedule: dict, number: str, hash_: str, folder: str = "import_schedule/buses") -> str:
    """
    Проверяет наличие файла по шаблону {number}_{hash}.json.
    Если найден файл с этим номером и совпадающим хэшем — выход.
    Если найден, но хэш отличается — удаляет старый и сохраняет новый.
    Если не найден — сохраняет новый файл.
    """
    prefix = f"{number}_"
    target_filename = f"{number}_{hash_}.json"

    for filename in os.listdir(folder):
        if filename.startswith(prefix) and filename.endswith(".json"):
            if filename == target_filename:
                # Файл уже существует с правильным хэшем — ничего не делаем
                return "Расписание не изменилось."
            else:
                # Старый файл — другой хэш. Удалим
                os.remove(os.path.join(folder, filename))

    # Сохраняем новый файл
    filepath = os.path.join(folder, target_filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=4)
    return "Расписание сохранено."


def merge_json_files(folder: str = "import_schedule/buses", output_filename: str = "result.json"):
    """
    Объединяет все JSON-файлы из указанной папки в один словарь.
    Каждое значение добавляется в виде элементов списка, упорядоченного по номерам.
    """
    merged = {}
    buses_present = []  # Эти автобусы обработаны
    print("Сборка файла импорта:")
    for filename in sorted(os.listdir(folder)):
        if filename.endswith(".json") and filename != output_filename:
            filepath = os.path.join(folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if not isinstance(data, dict):
                    print(f"Файл {filename} не является словарем. Исключен.")
                    continue  # Пропускаем невалидные файлы

                number = filename.split("_")[0]  # Номер автобуса
                # Исключаем автобус
                if number not in buses:
                    print(f"автобус {number} исключен")
                    continue

                buses_present.append(number)  # Добавляем автобус в список
                # Добавляем расписание в словарь
                merged[str(next(iter(data)))] = next(iter(data.values()))

            except Exception as e:
                print(f"Ошибка при чтении {filename}: {e}")
                continue

    # Сообщаем, для каких автобусов нет файлов-расписаний
    is_absent = list(set(buses) - set(buses_present))
    is_absent = sorted_buses(is_absent)  # Сортировка названий автобусов
    if is_absent:
        print(f"Для автобусов: {', '.join(is_absent)}\nнет расписаний.")

    # Упорядочим по номеру (если можно привести к int, иначе по строке)
    sorted_merged = {k: merged[k] for k in sorted(merged, key=cmp_to_key(compare_name))}

    with open(os.path.join(".", output_filename), 'w', encoding='utf-8') as f:
        json.dump(sorted_merged, f, ensure_ascii=False, indent=4)

    print("Файл импорта собран:")
