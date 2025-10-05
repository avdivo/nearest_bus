import re
from time import sleep, time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from import_schedule.import_schedule import (
    calculate_md5_from_dict,
    get_direction_and_bus_stop,
    merge_json_files,
    save_bus,
)
from import_schedule.logger_config import logger

# Если нужно создать сводный файл, но не парсить
merge_json_files()
exit(0)

"""
Пустой ввод - все расписание
Номер автобуса - только 1 автобус
Номер автобуса с тире - от указанного автобуса до конца
"""
while True:
    try:
        until_end = False  # Сканировать не до конца если указан 1 автобус
        import_number = input("Номер автобуса или пустой ввод (все): ")

        if not import_number:
            logger.info("Сканировать все расписание.")
            import_number = "_all_"
            break

        match = re.match(r"\d+", import_number)
        if not match or int(match.group()) > 21:
            raise ValueError("Нет такого автобуса")

        if import_number.endswith("-"):
            import_number = import_number.replace("-", "")
            logger.info(f"Сканировать от {import_number} до конца.")
            until_end = True  # Сканировать до конца расписания
        else:
            logger.info(f"Сканировать автобус № {import_number}.")

        break
    except ValueError as e:
        print(e)
        exit(0)

# Запускаем браузер
driver = webdriver.Chrome()

# Открываем сайт
url = "https://gpmopt.by/mopt/Home/Index/sluck#/routes/bus"
driver.get(url)
# Ожидание полной загрузки страницы
sleep(2)
# Получаем содержимое страницы
page_source = driver.page_source

time_start = time()
logger.warning("Начало получения расписания.")

# Находим номера маршрутов (номера автобусов) и записываем их в список
direction_len = len(driver.find_elements(By.XPATH, '//*[@id="routeList"]/li[*]/a'))

i = 0
result = dict()  # Словарь с результатами работы
hash = None
while direction_len - i:
    # Читаем найденные автобусы, получаем их номера.
    # Кликаем поочереди даля открытия маршрутов автобуса
    # Ждём, пока появится хотя бы один элемент в списке
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="routeList"]/li[1]/a'))
    )
    directions = driver.find_elements(By.XPATH, '//*[@id="routeList"]/li[*]/a')

    # Удаляем все непечатаемые символы (включая \n, \t, \xa0 и др.)
    cleaned_text = re.sub(
        r"[\x00-\x1F\x7F-\xA0\u200B-\u200F\u2028-\u202F]", " ", directions[i].text
    )
    bus_number = cleaned_text.split()[0]

    # Автобусы городских маршрутов кончились
    if bus_number == "201C" or bus_number == "201С":
        elapsed_time = time() - time_start
        # Разбиваем на часы, минуты и секунды
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)

        logger.warning(
            (
                f"Конец получения расписания. {int(hours)} ч {int(minutes)} мин "
                f"{int(seconds)} сек "
            )
        )
        # Это останавливает процесс, чтобы не
        # сканировать пригородные маршруты
        break

    print(cleaned_text, end="")

    # Нужно ли получать расписание для этого автобуса
    if import_number != "_all_" and bus_number != import_number:
        print(": пропущен.")
        i += 1
        continue

    if until_end:
        import_number = "_all_"  # Включаем сканирование до конца
        until_end = False

    print()
    logger.info(f"Автобус {bus_number}")
    # Ожидаем, что конкретный элемент стал кликабельным
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(directions[i]))
    directions[i].click()
    sleep(2)

    # Получение расписания с проверкой
    is_direction = 10
    while is_direction:
        direction = get_direction_and_bus_stop(driver)
        is_direction -= 1
        if not direction:
            sleep(2)
            continue
        is_direction = 0

    result = {bus_number: direction}  # Функция читает маршруты

    # Расписание прочитано 1 раз, или 2 раза
    if hash is None:
        # После первого прочтения запоминаем hash и читаем еще раз
        hash = calculate_md5_from_dict(result)
        driver.get(url)
        logger.info("Прочитано 1 раз")
        continue
    else:
        # После 2 прочтения принимаем решение о перепрочтении еще 2 раз
        if hash == calculate_md5_from_dict(result):
            # Сохраняем расписание автобуса в файл
            message = save_bus(result, bus_number, hash)
            hash = None
            i += 1
            driver.get(url)
            logger.info("Правильность чтения подтверждена.")
            logger.info("{message}")
            continue
        else:
            # Расписания полученные 2 раза оказались разными
            driver.get(url)
            logger.warning("Ошибка чтения. Повтор...")
            hash = None


# Собираем общее расписание
logger.warning("Сборка полного расписания...")
merge_json_files()
