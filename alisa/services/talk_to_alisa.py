# Модуль принимает запросы от сервиса Яндекс.Диалоги и возвращает ответы.
# Реализует функции навыка Слуцкие автобусы.

import re
import json
import logging
from difflib import SequenceMatcher

from schedule.models import BusStop, OptionsForStopNames

from alisa.services.functions import authorize
from alisa.services.analizer import select_samples_by_phrase
from tbot.services.executors import answer_for_alisa




def answer_to_alisa(request_body):
    """Функция получает все сообщения от Алисы. Определяет их статус и выполняет
    действия в соответствии с ним.
    Принимает тело запроса от Алисы."""

    def say_schedule(start, end, schedule):
        """Готовит ответ о расписании между двумя остановками.
        Принимает начальную и конечную остановки.
        Возвращает текст ответа."""
        user.set_parameters([start, end], 'stops')  # Запоминаем начальную и конечную остановки для повтора
        limit = 2
        text = f'Ближайшие автобусы по маршруту {start} - {end} в '
        if len(schedule) > 1:
            for time, buses in schedule.items():
                if limit == 0:
                    break
                text += f'{time} - '
                word = 'автобус номер' if len(buses) == 1 else 'автобусы номер'
                text += f'{word} {" ,".join(buses)}. '
                limit -= 1
                user.set_parameters(time, 'time')  # Запоминаем последнее названное время
        return text

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
        return ('Извиняюсь, я вас не поняла. '
                'Пожалуйста, повторите или уточните названия остановок.')

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
                return ('Шаркнула ножкой!')

            elif out[0] == 'Повтори':
                stops = user.get_parameters('stops')
                if stops:
                    return say_schedule(stops[0], stops[1], user.get_parameters('schedule'))
                else:
                    return ('Пожалуйста, назовите маршрут, чтобы узнать расписание.')

            elif out[0] == 'Дальше':
                if user.get_parameters('schedule'):
                    # Имеем словарь {время (str): [автобус1, автобус2]}, ищем в нем уже названное время
                    # Переходим к следующему и называем его
                    schedule = user.get_parameters('schedule')
                    time = user.get_parameters('time')
                    times = list(schedule.keys())
                    index = times.index(time)
                    index += 1
                    if index > len(times)-1:
                        index = 0
                    time = times[index]
                    buses = schedule[time]
                    user.set_parameters(time, 'time')  # Запоминаем последнее названное время
                    word = 'автобус номер' if len(buses) == 1 else 'автобусы номер'
                    return f'в {time} - {word} {" ,".join(buses)}.'
                else:
                    return ('Пожалуйста, назовите маршрут, чтобы узнать расписание.')

            else:
                return ('Извиняюсь, я вас не поняла. '
                        'Пожалуйста, повторите или уточните названия остановок.')

        return (f'Извиняюсь, я расслышала только одну остановку: {out[0]}. '
                f'Пожалуйста, повторите или уточните названия остановок.')

    elif len(out) == 2:
        try:
            # Список автобусов на остановке
            schedule = answer_for_alisa(out[0], out[1])
        except:
            # Если остановка не найдена, то выводим сообщение и завершаем действие
            return (f'Между остановками {out[0]} и {out[1]} нет прямого автобуса. '
                    f'Пожалуйста, выберите другой маршрут.')

        user.set_parameters(schedule, 'schedule')  # Запоминаем расписание для команды "Дальше"

        # Увеличение счетчика выдачи расписаний для пользователя.
        user.schedule_count += 1
        user.save()

        return say_schedule(out[0], out[1], schedule)

    else:
        return (f'Я не смогла понять вашу команду, вот что я услышала {", ".join(out)}. ')
