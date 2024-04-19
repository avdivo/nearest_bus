from selenium import webdriver
from selenium.webdriver.common.by import By
import re
import time

# Запускаем браузер
driver = webdriver.Chrome()

# Открываем сайт
url = "https://vslutske.by/transport/raspisanie-avtobusov/"
driver.get(url)

# Получаем содержимое страницы
page_source = driver.page_source

# Выводим содержимое страницы

# Находим все элементы <div> с классом "bus-route-title"
buses = driver.find_elements(By.XPATH, '//div[@class="bus-route-container"]')

"""Словарь со структурой 
{   
    маршрут: {
        направление: {
            остановка: расписание
        }
    }
}
"""
all_schedule = dict()
path_in_dict = all_schedule  # Тут словарь (ветка) словаря с которым работаем

# Это спойлеры маршрутов, открывая которые получаем расписание.
# В нем первая кнопка для открытия модального окна с расписанием по остановкам.
# Могут быть кнопки дополнительных маршрутов,
# открывающие модальные окна с их расписаниям по остановкам
for bus in buses:
    bus_numer = number = re.search(r'№\s*([^ ]+)', bus.text).group(1)
    bus.click()  # Открываем спойлер
    time.sleep(0.2)
    modals = bus.find_elements(By.CSS_SELECTOR, ".by-points")

    # Разбираем содержимое спойлера
    # Список кнопок открывающих модальные окна
    # Первая кнопка - расписание для основного маршрута
    one = True
    for modal in modals:
        if one:
            # Если это переход к окну расписания основного маршрута (первая кнопка), то номер автобуса мы уже имеем
            one = False
        else:
            # Получаем номер дополнительного автобуса
            bus_numer = number = re.search(r'№\s*([^ ]+)', modal.text).group(1)

        path_in_dict[bus_numer] = dict()  # Добавляем словарь для маршрута в основной словарь
        path_in_dict = path_in_dict[bus_numer]  # Теперь работаем с вложенным словарем в рамках сохраненного маршрута

        modal.click()  # Открываем модальное окно
        time.sleep(1)

        # Находим элемент модального окна с помощью CSS-селектора
        modal_elements = driver.find_elements(By.CSS_SELECTOR, "#modal-container")

        # Проверяем, был ли найден элемент модального окна
        if not modal_elements:
            continue

        # Получение списка спойлеров маршрутов (конечная-конечная)
        containers = modal_elements[0].find_elements(By.CSS_SELECTOR, "[class*='route-'][class$='container']")

        for container in containers:
            path_in_dict[container.text] = dict()  # Добавляем словарь для направления в словарь маршрута
            path_in_dict = path_in_dict[container.text]  # Теперь работаем с вложенным словарем
            container.click()  # Открываем спойлер
            time.sleep(0.2)

            bus_points = container.find_elements(By.CSS_SELECTOR, ".bus-point")  # Под спойлером список остановок


            for bus_point in bus_points:
                print(bus_points)
                direction = re.sub(r'[^\w\s]', '', bus_point.text)  # Очищаем текст
                print(bus_point.text)

                path_in_dict[direction] = dict()  # Добавляем словари остановок в словарь направления
                path_in_dict = path_in_dict[direction]  # Теперь работаем с вложенным словарем

                modal_contents = modal_elements[0].find_element(By.XPATH, "//div[@id='modal-container']").get_attribute("outerHTML")

                bus_point.click()  # Переходим к расписанию
                time.sleep(0.5)

                print(modal_elements[0].text)

                # Восстанавливаем содержимое модального окна
                driver.execute_script('''
                    var modal = document.createElement("div");
                    modal.innerHTML = arguments[0];
                    var modalContainer = document.getElementById("modal-container");
                    modalContainer.innerHTML = "";
                    modalContainer.appendChild(modal);
                ''', modal_contents)

                bus_points = driver.find_elements(By.CSS_SELECTOR, ".bus-point")  # Под спойлером список остановок
                print(bus_points[0].text)
            # print(all_schedule)
exit()
#     # Получаем все кнопки
#     modals = driver.find_elements(By.XPATH, '//div[@class="by-points"]')
#     time.sleep(0.2)
#
#
#     for modal in modals:
#         if not modal.text:
#             continue
#         print(modal.text)
#         modal.click()
#         time.sleep(1)
# #
#         # Находим элемент модального окна с помощью CSS-селектора
#         modal_elements = driver.find_elements(By.CSS_SELECTOR, "#modal-container")
# #
# #         # Получаем содержимое модального окна
# #         modal_content = ""
# #         for element1 in modal_elements:
# #             modal_content += element1.text
# # #
# #         # Выводим содержимое модального окна на экран
# #         print(modal_content)
# #
#
#         # Получение списка спойлеров маршрутов (конечная-конечная)
#         containers = modal_elements[0].find_elements(By.CSS_SELECTOR, "[class*='route-'][class$='container']")
#         # Получение остановок на маршрутах
#         bus_points = modal_elements[0].find_elements(By.CSS_SELECTOR, "[class='bus-point']")
#         print(len(bus_points))
#         print(containers)
#         for container in containers:
#             print(container.text)
#             container.click()
#             for container in bus_points:
#                 print(container.text)
#
#
#
#         # Проверяем, был ли найден элемент модального окна
#         if len(modal_elements) > 0:
#             # Находим кнопки-спойлеры открывающие список остановок
#
#             # Найдем элемент закрытия модального окна
#             close_button = modal_elements[0].find_element(By.ID, "modal-close")
#             # Нажать на элемент закрытия модального окна
#             close_button.click()
# #
#         time.sleep(0.2)
#
#     bus.click()
#
#
#
# # Открываем каждый спойлер, находим вложенные элементы и распечатываем текст
# # for spoiler in spoilers:
# #     spoiler.click()  # Кликаем по спойлеру
# #     # time.sleep(1)  # Ждем некоторое время, чтобы контент успел загрузиться
# #
# #     nested_elements = spoiler.find_elements("xpath", "./following-sibling::*")
# #     for element in nested_elements:
# #         html_content = element.get_attribute("outerHTML")
# #         print(html_content)
#
#
# # Закрываем браузер
# driver.quit()


