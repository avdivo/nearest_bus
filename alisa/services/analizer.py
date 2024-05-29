# Модуль для анализа речи, распознавания команд и маршрутов

import re
import logging
from num2words import num2words
from difflib import SequenceMatcher
from Levenshtein import distance


logger = logging.getLogger('alisa')


def text_preparation(text):
    """Подготовка текста к анализу.
    Переводит в нижний регистр,
    удаляет знаки препинания и др. оставляя только буквы и цифры,
    меняет букву ё на ё.
    Возвращает обработанный текст.
    """
    text = text.lower().replace('ё', 'е')
    text = re.sub(r'\W+', ' ', text)
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
        similarity_ratio = SequenceMatcher(None, word.strip(), stop.strip()).ratio()  # Сравниваем
        # similarity_ratio = 1 - distance(word.strip(), stop.strip()) / max(len(word.strip()), len(stop.strip()))  # Сравниваем
        if similarity_ratio > best_match_ratio:
            # Выбираем лучший результат
            best_match = original_name
            best_match_ratio = similarity_ratio

    return best_match, best_match_ratio


def select_samples_by_phrase(phrase, anything_list, add_dict) -> list:
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
    words_start = phrase.split()

    # Удаляем из не желательные слова.
    # Меняем числа на слова
    delete_words = ['алиса', 'улиц', 'номер']
    words = []
    for word in words_start:
        # меняем числа на слова
        if word.isdigit():
            word = num2words(word, lang='ru')
        ok = True
        for delete_word in delete_words:
            if delete_word in word:
                ok = False
        if ok and word not in words:
            words.append(word)

    print(words)  # Что расслышано и не отфильтровано
    logger.warning(f"Запрос к Алисе:\n{' '.join(words)}")

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
            if best_stop not in mem:
                mem.append(best_stop)  # Этот результат принят
            new_phrase = word
            best_result = 0
            best_stop = ''
            matching_stops = find_matching_stop(new_phrase, anything_list, add_dict)
            if matching_stops[1] > 0.5:
                # Записываем только слова с хорошим совпадением
                best_result = matching_stops[1]
                best_stop = matching_stops[0]
    if best_stop and best_stop not in mem:
        mem.append(best_stop)

    return mem


