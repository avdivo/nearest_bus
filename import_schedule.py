from selenium import webdriver
from selenium.webdriver.common.by import By
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
buses = driver.find_elements(By.XPATH, '//div[@class="bus-route-title"]')

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


# Это спойлеры маршрутов, открывая которые получаем расписание.
# В нем первая кнопка для открытия модального окна с расписанием по остановкам.
# Могут быть кнопки дополнительных маршрутов,
# открывающие модальные окна с их расписаниям по остановкам
for bus in buses:
    bus.click()
    # Получаем все кнопки
    modals = driver.find_elements(By.XPATH, '//div[@class="by-points"]')
    time.sleep(0.2)


    for modal in modals:
        if not modal.text:
            continue
        print(modal.text)
        modal.click()
        time.sleep(1)
#
        # Находим элемент модального окна с помощью CSS-селектора
        modal_elements = driver.find_elements(By.CSS_SELECTOR, "#modal-container")
#
#         # Получаем содержимое модального окна
#         modal_content = ""
#         for element1 in modal_elements:
#             modal_content += element1.text
# #
#         # Выводим содержимое модального окна на экран
#         print(modal_content)
#

        # Получение списка спойлеров маршрутов (конечная-конечная)
        containers = modal_elements[0].find_elements(By.CSS_SELECTOR, "[class*='route-'][class$='container']")
        # Получение остановок на маршрутах
        bus_points = modal_elements[0].find_elements(By.CSS_SELECTOR, "[class='bus-point']")
        print(len(bus_points))
        print(containers)
        for container in containers:
            print(container.text)
            container.click()
            for container in bus_points:
                print(container.text)



        # Проверяем, был ли найден элемент модального окна
        if len(modal_elements) > 0:
            # Находим кнопки-спойлеры открывающие список остановок

            # Найдем элемент закрытия модального окна
            close_button = modal_elements[0].find_element(By.ID, "modal-close")
            # Нажать на элемент закрытия модального окна
            close_button.click()
#
        time.sleep(0.2)

    bus.click()



# Открываем каждый спойлер, находим вложенные элементы и распечатываем текст
# for spoiler in spoilers:
#     spoiler.click()  # Кликаем по спойлеру
#     # time.sleep(1)  # Ждем некоторое время, чтобы контент успел загрузиться
#
#     nested_elements = spoiler.find_elements("xpath", "./following-sibling::*")
#     for element in nested_elements:
#         html_content = element.get_attribute("outerHTML")
#         print(html_content)


# Закрываем браузер
driver.quit()


