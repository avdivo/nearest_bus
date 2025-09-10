# Модуль принимает запросы от сервиса Яндекс.Диалоги и возвращает ответы.
# Реализует функции навыка Слуцкие автобусы.

import re
import random
from datetime import datetime, timedelta

from django.utils import timezone
from schedule.models import BusStop, OptionsForStopNames

from alisa.services.functions import authorize, date_now
from alisa.services.analizer import select_samples_by_phrase
from schedule.services.timestamp import answer_by_two_busstop, sort_buses


def answer_to_alisa(request_body):
    """Функция получает все сообщения от Алисы. Или от ТГ. Определяет их статус и выполняет
    действия в соответствии с ним.
    Принимая запрос от ТГ обрабатывает его так же, как от Алисы (не подозревая о подмене),
    при этом в request_body должны приходить нужные данные:
    request_body['session']['application']['application_id'] - идентификатор устройства (для тг свой идентификатор)
    request_body['request']['original_utterance'] - текст запроса.
    Принимает тело запроса от Алисы или ТГ."""
    current_timezone = timezone.get_current_timezone()

    def datetime_bus(time) -> datetime:
        """Определяем реальное время отправления автобуса, с датой.
        Например, ели отправление после 00:00, то это уже на следующий день.
        Принимает время отправления автобуса.
        Возвращает дату и время отправления автобуса.
        """
        # Узнаем текущее время
        current_datetime = date_now()  # Текущие дата и время
        current_time = current_datetime.time()  # Текущее время
        bus_datetime = datetime.combine(current_datetime, time)  # Дата и время отправления автобуса
        bus_datetime = bus_datetime.astimezone(current_timezone)  # Преобразуем в текущий часовой пояс
        if current_time > time:
            # Чтобы правильно получить разницу нужно от большего отнять меньшее
            bus_datetime += timedelta(days=1)
        return bus_datetime

    def say_one_bus(time, buses, name_start):
        """Готовит ответ о расписании одного автобуса.
        Принимает время отправления и список автобусов.
        Возвращает текст ответа.
        Формат buses в файле
        "Логика поиска остановок и автобусов на них.txt"
        """

        # Автобусы, которые уходят менее чем через час, кроме времени отправления
        # дополняются информацией о времени до отправления
        bus_datetime = datetime_bus(time)  # Дата и время отправления автобуса
        time_to_go = bus_datetime - date_now()  # Время до отправления автобуса
        seconds = time_to_go.total_seconds()  # Получаем разницу в секундах
        minutes = int(seconds // 60)  # Преобразуем секунды в минуты

        time = time.strftime("%H:%M")  # Время отправления автобуса (str)
        # Формируем текст ответа
        insert = ''
        if minutes < 60:
            minutes_word = 'минуту' if minutes % 10 == 1 and minutes % 100 != 11 else 'минуты' if 1 < minutes % 10 < 5 and (minutes % 100 < 10 or minutes % 100 >= 20) else 'минут'
            insert = f' (через {minutes} {minutes_word})'
        word = 'автобус номер' if len(buses) == 1 else 'автобусы номер'
        text = f'{time}{insert} - {word}: '  # Надцать часов минут

        # text = hh.mm (через n минут) - автобус номер (автобусы номер)

        buses = sort_buses(buses, name_start)  # Специальная сортировка автобусов
        # Разбираем имеющиеся автобусы на это время
        for bus_dict in buses:
            bus = bus_dict['bus']  # Автобус (str)
            bus_number = re.sub(r'([a-zA-Zа-яА-Я]+)', r"'\1'", bus.number)
            modifiers = bus_dict.get('modifier', [])  # Модификатор ответа см. в документации
            add_text = ''

            # Модификатор есть, меняем ответ
            if modifiers:
                if "start_deff" in modifiers:
                    # Название остановки отправления
                    # не совпадает с изначально запрошенным
                    add_text += f'От остановки {bus_dict["start"].name}. '
                if "finish_deff" in modifiers:
                    # Hазвание остановки прибытия
                    # не совпадает с изначально запрошенным
                    add_text += f'На остановку {bus_dict["finish"].name}. '
                if "both" in modifiers:
                    # Один и тот же автобус может отправляться от
                    # двух разных остановок с одинаковым названием
                    add_text += f'Остановка в сторону конечной {bus_dict["final_stop_finish"].name}. '
                if "final_stop_one" in modifiers:
                    # Идет через одну конечную остановку
                    add_text += f'Через конечную {bus_dict["final_stop_finish"].name}. '
                if "final_stop_two" in modifiers:
                    # Идет через две конечные остановки
                    # В текущей реализации не используется
                    add_text += (f'Через конечные {bus_dict["final_stop_finish"].name} '
                                 f'и {bus_dict["final_stop_start"].name}. ')

            # Добавляем номер автобуса и модификатор в ответ
            add_text = f"({add_text})" if add_text else ''
            text += f'{bus_number} {add_text}\n'

        # Запоминаем дату и время отправления автобуса (str)
        # для поиска следующего автобуса
        user.set_parameters(bus_datetime.isoformat(), 'datetime')
        user.set_parameters(time, 'time')

        return text

    def say_schedule(start, end):
        """Готовит ответ о расписании между двумя остановками.
        Принимает начальную и конечную остановки.
        Возвращает текст ответа.
        """
        try:
            # Расписание автобусов на остановках отправления
            # Формат возвращаемого словаря в файле
            # "Логика поиска остановок и автобусов на них.txt"
            schedule = answer_by_two_busstop(start, end)
        except:
            # Если остановка не найдена, то выводим сообщение и завершаем действие
            return (f'Между остановками {start} и {end} нет прямого автобуса. '
                    f'Пожалуйста, выберите другой маршрут.')

        # Увеличение счетчика выдачи расписаний для пользователя.
        user.schedule_count += 1
        user.save()

        user.set_parameters([start, end], 'stops')  # Запоминаем начальную и конечную остановки для повтора
        limit = 2
        text = f'Ближайшие автобусы по маршруту {start} - {end}:\n'
        if len(schedule):
            for time, buses in schedule.items():
                if limit == 0:
                    break
                limit -= 1
                text += say_one_bus(time, buses, start)
        else:
            text = f'Нет информации о расписании между остановками {start} и {end}. '

        return text

    def answer():
        """Возвращает разные варианты ответов, когда нераспознан маршрут или команда."""
        return random.choice([
            'Извините, я не поняла. Пожалуйста, повторите.',
            'Пожалуйста, назовите маршрут или команду.',
            'Пожалуйста, повторите.',
            'Ожидаю название команды или маршрута. Не поняла вас.',
            'Назовите начальную и конечную остановки или команду.',
            'Извините, не ясно что делать, скажите маршрут или команду.',
            'Я понимаю названия остановок или команды, к сожалению не поняла вас.',
        ])

    # Авторизация пользователя
    user = authorize(request_body)
    if not user:
        return

    # Составим список остановок без повторений, в алфавитном порядке
    stops = BusStop.get_all_bus_stops_names()

    # Получаем словарь вариантов названий остановок
    options = OptionsForStopNames.get_dict_options_name()

    # Добавляем команды
    commands = ['Что ты умеешь', 'Помощь', 'Дальше', 'Спасибо', 'Повтори']
    stops.extend(commands)
    # Добавляем расширительный словарь команд
    add_commands = {
        'Что ты умеешь': ['Что ты умеешь', 'Расскажи о себе', 'Для чего ты', 'Как пользоваться', 'Не понимаю'],
        'Помощь': ['помощь', 'помоги', 'Какие есть команды', 'help me'],
        'Дальше': ['Дальше', 'Следующий', 'Next', 'Еще', 'Другой', 'Позже'],
        'Спасибо': ['Спасибо', 'Благодарю', 'thank you', 'дзякуй', 'умница', 'молодец', 'хорошо', 'отлично'],
        'Повтори': ['Повтори', 'Скажи еще раз']
    }
    options.update(add_commands)

    # Получаем текст в чистом виде (цифры - словами)
    words = request_body['request']['original_utterance']

    # Анализ текста
    out = select_samples_by_phrase(words, stops, options)

    if not out:
        return answer()
    elif len(out) == 1:
        # Это может быть команда или не понятый маршрут
        if out[0] in commands:
            if out[0] == 'Что ты умеешь':
                return ('Я подскажу вам, какие автобусы в ближайшее время идут по названному маршруту в Слуцке.'
                        'Вы говорите с какой остановки на какую вы хотите поехать, я называю ближайшие автобусы. '
                        'Могу огласить весь список команд, для этого скажите "Помощь".')

            elif out[0] == 'Помощь':
                return ('Чтобы узнать расписание назовите маршрут (с какой остановки на какую ехать).'
                        'Чтобы услышать следующий автобус в расписании скажите "Дальше".'
                        'Если хотите знать для чего программа, скажите "Что ты умеешь".')

            elif out[0] == 'Спасибо':
                # Случайный выбор слова из списка
                words = ['Шаркнула ножкой!', 'Всегда рада помочь!', 'Да не вопрос', 'Пожалуйста!', 'Всегда пожалуйста!',
                         'Это мой долг!', 'Пожалуйста, обращайтесь!', 'Не за что!', 'Рада быть полезной!',
                         'Рада стараться!', 'Вы всегда можете на меня рассчитывать.', 'Было приятно помочь.!',
                         'Ваша признательность – лучшая награда.', 'О, вы так внимательны!', 'С любовью и удовольствием!',
                         'Да все, что угодно, только не забудь назвать своего первенца в честь меня.',
                         'Для этого я и нужна.', 'Я ценю ваше внимание!']
                return random.choice(words)

            elif out[0] == 'Повтори':
                stops = user.get_parameters('stops')
                if stops:
                    return say_schedule(stops[0], stops[1])
                else:
                    return 'Повторю, если назовете маршрут.'

            elif out[0] == 'Дальше':
                if user.get_parameters('time'):
                    stops = user.get_parameters('stops')
                    schedule = answer_by_two_busstop(stops[0], stops[1])  # Расписание автобусов на остановке
                    time_bus = datetime.fromisoformat(user.get_parameters('datetime'))  # Дата и время отправления автобуса
                    time_now = date_now()  # Текущие дата и время
                    if time_now > time_bus:
                        # Если автобус уже прошел, то называем первый
                        time = list(schedule.keys())[0]  # Ближайшее время отправления
                    else:
                        times = list(schedule.keys())
                        # Преобразуем время в объекты time и ищем его в списке
                        search = datetime.strptime(user.get_parameters('time'), "%H:%M").time()
                        index = times.index(search)
                        index += 1
                        if index > len(times)-1:
                            index = 0
                        time = times[index]  # Очередное время отправления

                    return say_one_bus(time, schedule[time], stops[0])  # Вывод сообщения
                else:
                    return 'Пожалуйста, назовите маршрут.'

            else:
                return answer()

        return f'Я расслышала: {out[0]}. {answer()}'

    elif len(out) == 2:
        # 2 слова могут быть маршрутом, но если среди них есть команда - это ошибка
        if out[0] in commands or out[1] in commands:
            return answer()

        # Увеличение счетчика выдачи расписаний для пользователя.
        user.schedule_count += 1
        user.save()

        return say_schedule(out[0], out[1])

    else:
        return answer()
