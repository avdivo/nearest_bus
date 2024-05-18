# Модуль принимает запросы от сервиса Яндекс.Диалоги и возвращает ответы.
# Реализует функции навыка Слуцкие автобусы.

import re
import json
import logging
from difflib import SequenceMatcher

from schedule.models import BusStop, OptionsForStopNames

from alisa.services.functions import authorize
from tbot.services.executors import answer_for_alisa


def text_preparation(text):
    """Подготовка текста к анализу.
    Переводит в нижний регистр,
    удаляет знаки препинания и др. оставляя только буквы и цифры,
    меняет букву ё на ё.
    Возвращает обработанный текст.
    """
    text = text.lower().replace('ё', 'е')
    text = re.sub(r'\W+ ', '', text)
    return text


def find_matching_stop(word, anything_list, options):
    """Сущность - это шаблонная фраза (название остановки, команда).
    Поиск наиболее похожего названия сущности из списка имеющихся.
    Принимает искомое слово и список в котором будет искать. Расширительный словарь:
    названия в основном списке как ключи в словаре из которого можно брать варианты слов
    {Название: [Вариант1, Вариант2,...]}.
    Ищет похожие названия из списка и расширенного списка (словаря) для некоторых.
    Возвращает название сущности (правильное, из основного списка) и степень его схожести)."""
    best_match = None
    best_match_ratio = 0

    def name_generator(stops, options):
        """Генератор.
        Возвращает имена сущностей (остановок) в преобразованном виде
        (только буквы и цифры в нижнем регистре, ё - заменена на е.
        И оригинальные имена (кортеж).
        Получает список сущностей и дополнительный словарь в котором указаны
        варианты названия некоторых  {Название: [Вариант1, Вариант2,...]}.
        Если у сущности есть варианты - возвращает их, если нет - только ее название."""
        for stop in stops:
            if stop in options:
                for option in options[stop]:
                    name = text_preparation(option)
                    yield name, stop
            else:
                name = text_preparation(stop)
                yield name, stop

    # Перебор всех сущностей, поиск в них похожих на искомое слов
    stops_list = name_generator(anything_list, options)  # Получаем очередную сущность
    for stop, original_name in stops_list:
        similarity_ratio = SequenceMatcher(None, word, stop).ratio()  # Сравниваем
        if similarity_ratio > best_match_ratio:
            # Выбираем лучший результат
            best_match = original_name
            best_match_ratio = similarity_ratio

    return best_match, best_match_ratio


def select_samples_by_phrase(phrase, anything_list, add_dict):
    """Ищет и возвращает наиболее подходящие встречаемые в переданном тексте шаблонные фразы
    из списка фраз и расширительного словаря. Пример:
    'Найди автобус от социалистической до мясокомбината' -
    в этой фразе должна вернуть ['Социалистическая', 'Мясокомбинат'].
    Не сильно тестировалось на другое количество фраз, кроме 1 и 2.
    Принимает фразу, список шаблонных фраз, расширительный словарь вида
    {Название: [Вариант1, Вариант2,...]}.
    Возвращает список шаблонных фраз (оригинальных) в порядке встреченном во фразе.
    """
    # Обработка текста, получение токенов
    phrase = text_preparation(phrase)
    words = phrase.split()

    # Удаляем из не желательные слова
    delete_words = ['автобус', 'алиса']
    for delete_word in delete_words:
        try:
            words.remove(delete_word)
        except:
            pass
    print(words)

    new_phrase = '' # Часть искомой фразы
    mem = []  # Найденные фразы
    best_result = 0  # Лучшее совпадение фразы
    best_stop = ''  # Фраза с лучшим совпадением
    # Перебираем слова в разбираемой фразе и ищем совпадения с шаблонными фразами
    # по принципу: берем слово, находим фразу с которой у него лучшее совпадение,
    # добавляем слово, если совпадение улучшилось - добавляем следующее слово,
    # если ухудшилось - добавляем найденную фразу (с предыдущим, лучшим показателем
    # совпадения) в список найденных.
    # Очищаем найденную фразу и берем последнее слово и с него продолжаем..
    for word in words:
        # Ищем совпадающую фразу
        matching_stops = find_matching_stop(new_phrase + ' ' + word, anything_list, add_dict)
        if matching_stops[1] < 0.5:
            # Если это слово имеет плохое совпадение с фразами, то пропускаем его
            continue
        if matching_stops[1] > best_result:
            # Если совпадение улучшилось, то добавляем слово к фразе
            best_result = matching_stops[1]
            best_stop = matching_stops[0]
            new_phrase += ' ' + word
        elif matching_stops[1] < best_result:
            # Если совпадение ухудшилось, то добавляем найденную фразу в список
            mem.append(best_stop)  # Этот результат принят
            new_phrase = word
            best_result = 0
            best_stop = ''
            matching_stops = find_matching_stop(new_phrase, anything_list, add_dict)
            if matching_stops[1] > 0.5:
                # Записываем только слова с хорошим совпадением
                best_result = matching_stops[1]
                best_stop = matching_stops[0]
    if best_stop:
        mem.append(best_stop)

    return mem


def answer_to_alisa(request_body):
    """Функция получает все сообщения от Алисы. Определяет их статус и выполняет
    действия в соответствии с ним.
    Принимает тело запроса от Алисы."""
    user = authorize(request_body)
    if not user:
        return

    # Составим список остановок без повторений, в алфавитном порядке
    stops = BusStop.get_all_bus_stops_names()

    # Получаем словарь вариантов названий остановок
    options = OptionsForStopNames.get_dict_options_name()

    # Получаем текст в чистом виде (цифры - словами)
    words = request_body['request']['original_utterance']
    out = select_samples_by_phrase(words, stops, options)

    if not out:
        return ('Извиняюсь, я вас не поняла. '
                'Пожалуйста, повторите или уточните названия остановок.')

    elif len(out) == 1:
        return (f'Извиняюсь, я расслышала только одну остановку: {out[0]}. '
                f'Пожалуйста, повторите или уточните названия остановок.')

    elif len(out) == 2:
        try:
            # Список автобусов на остановке
            schedule = answer_for_alisa(out[0], out[1])
        except AttributeError:
            # Если остановка не найдена, то выводим сообщение и завершаем действие
            return (f'Между остановками {out[0]} и {out[1]} нет прямого автобуса. '
                    f'Пожалуйста, выберите другой маршрут.')

        # Формируем ответ
        user.schedule_count += 1
        user.save()

        limit = 2
        text = f'Ближайшие автобусы по маршруту {out[0]} - {out[1]} в '
        if len(schedule) > 1:
            for time, buses in schedule.items():
                if limit == 0:
                    break
                text += f'{time} - '
                word = 'автобус номер' if len(buses) == 1 else 'автобусы номер'
                text += f'{word} {" ,".join(buses)}. '
                limit -= 1

        return text

    else:
        return (f'Я услышала больше двух остановок {", ".join(out)}. ')






    # application_id = request['session']['application']['application_id']
    # user = AlisaUser.authorize(application_id)
    # if user is None:
    #     text = ('Здравствуйте. Я подскажу вам, какие автобусы проходят в ближайшее время '
    #             'на выбранной вами остановке в Слуцке. Обратите внимание, для работы мне '
    #             'нужен доступ к вашим данным в телеграмм боте "Ближайший автобус в Слуцке". '
    #             'Вам необходимо войти в бот, выбрать в меню "Связь с Алисой" и написать '
    #             'Парольную фразу, по которой я вас узнаю. Сообщите мне эту парольную фразу.' )
    #     return {
    #         "response": {
    #             "text": text,
    #             "tts": text,
    #             "end_session": False
    #         },
    #         "session_state": {
    #             "value": "authorize"
    #         },
    #         "version": "1.0"
    #     }
    #
    # what_can_you_do = ('Я подскажу вам, какие автобусы проходят в ближайшее время '
    #                    'на выбранной вами остановке в Слуцке. '
    #                    'Назовите маршрут и я сообщу вам время прибытия ближайших автобусов.')
    # help_text = ('Чтобы услышать список маршрутов скажите "Маршруты".'
    #              'Назовите маршрут, чтобы узнать время прибытия ближайших автобусов на остановку.'
    #              'Для получения информации о следующем автобусе скажите "Следующий".')