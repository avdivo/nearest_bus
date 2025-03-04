"""Модуль для анализа речи, распознавания команд и маршрутов и объектов.
В этой версии реализовано более точное распознавание имеющихся объектов,
с меньшим количеством ложных срабатываний, что дает возможность пропускать
незнакомые объекты для дальнейшей разборки с помощью ИИ.
В списке объектов теперь можно хранить не только остановки, но и названия других
объектов и улиц.
Теперь, объект имеющийся в списке, будет не распознан, если после него идет цифра.
Это сделано для пропуска адресов, поскольку некоторые остановки имеют названия улиц и
распознаются по этому названию как остановки. Например: Тутаринова. Если будет
Тутаринова 15, такая запись будет пропущена. Соответственно и Дом быта 11 будет пропущена,
но это не должно сказаться на работе программы, поскольку такое название не имеет смысла.

"""

import re
import logging
from num2words import num2words
# from word2number_ru import w2n
from rapidfuzz import process, fuzz

logger = logging.getLogger('alisa')

LIMIT = 70  # Порог, при значении ниже которого новое слово для сущности бракуется
RESOLVE = 85  # Если баллы выше или равны этому значению - сущность признается


def remove_similar_words(word_list: list, delete_list: list, threshold=70) -> list:
    """Удаление из списка слов похожих на слова в списке удаления."""
    filtered_words = []

    for word in word_list:
        match, score, _ = process.extractOne(word_list, delete_list, scorer=fuzz.ratio)
        if score < threshold:  # Если слово недостаточно похоже, оставляем его
            filtered_words.append(word)

    return filtered_words


def text_preparation(text):
    """Подготовка текста к анализу:
    - переводит в нижний регистр
    - удаляет знаки препинания и др. оставляя только буквы и цифры
    - меняет букву ё на ё
    - меняет числа на слова.
    Возвращает обработанный текст.
    """
    text = text.lower().replace('ё', 'е')
    text = re.sub(r'\W+', ' ', text)

    # Замена в тексте чисел словами
    def replace_match(match):
        number = match.group()
        return num2words(int(number), lang='ru')

    # Заменяем числа в тексте
    return re.sub(r'\b\d+\b', replace_match, text)


def select_samples_by_phrase(phrase: str, anything_list: list, add_dict: dict, threshold: int = 90) -> list:
    """Ищет и возвращает наиболее подходящие встречаемые в переданном тексте шаблонные фразы
    из списка фраз и расширительного словаря. Пример:
    'Найди автобус от социалистической до мясокомбината' -
    в этой фразе должна вернуть ['Социалистическая', 'Мясокомбинат'].
    Возвращает список шаблонных фраз (оригинальных) в порядке встреченном во фразе.
    """

    # Подготовка словаря из списка и словаря
    # Ключи словаря будут названия объектов как в БД,
    # А значениями списки альтернативных названий, но:
    # в нижнем регистре, ё=е, числа заменены словами, без знаков препинания.
    alter_dict = {}
    for word in anything_list:
        new_list = {text_preparation(word)}
        if word in add_dict:
            for item in add_dict[word]:
                new_list.add(text_preparation(item))
        alter_dict[word] = new_list

    # Обработка текста, получение токенов
    phrase = text_preparation(phrase)
    words_start = phrase.split()

    # Удаляем нежелательные слова.
    # Меняем числа на слова
    delete_words = ['алиса', 'номер']
    words = remove_similar_words(words_start, delete_words)
    print(words)
    logger.warning(f"Запрос к Алисе:\n{' '.join(words)}")

    """
    Алгоритм поиска сущностей.
    1. Получаем список слов (фразу) в words
    2. index = 0, указатель на слово во фразе
       count = 1, количество слов в сущности.
       (Это текущая (предполагаемая) сущность выделенная в words)
       
       limit = 50, порог, при значении ниже которого новое слово для сущности бракуется
    3. Цикл пока index + count <= длины фразы words
    4. Сопоставляем текущую сущность со всеми списками альтернативного словаря,
       находим максимальный балл совпадения best, сущность и чем она найдена temp
    5. Если лучший балл (best) меньше порога (limit) то:
       - если limit >= 90 - запоминаем новую сущность entities d out_entities, 
         index = index + count - 1, count = 1
       - если limit < 90 - index = index + 1 (переходим к следующему слову)
       - limit = 50
       - entities = None
       - перейти к п.3
    6. Если лучший балл (best) больше порога (limit) то:
       - limit = best, count = count + 1, entities = temp
       - перейти к п.3
    7. Произошел выход из цикла:
       если есть entities - запоминаем ее в out_entities
    8. Возвращаем сущности out_entities или производим дальнейшую обработку.
    """

    found_entities = {}  # Словарь найденных сущностей {name: name in text}
    pre_entities = {}  # Вероятная сущность

    # Это текущая (предполагаемая) сущность выделенная в word
    index = 0  # Указатель на слово во фразе
    count = 1  # Количество слов в сущности

    limit = LIMIT

    while index + count <= len(words):
        # Находим лучшее соответствие среди всех сущностей
        best = 0
        temp_entities = None
        for name, alter_list in alter_dict.items():
            match, score, _ = process.extractOne(' '.join(words[index: index+count]), alter_list, scorer=fuzz.token_sort_ratio)
            if score >= best:
                print(' '.join(words[index: index+count]), alter_list, match, score, best)
                best = score
                temp_entities = {name: words[index: index+count]}
        print(pre_entities, best)
        if best < limit:
            # Показатель совпадения с новым словом низкий или ухудшился
            if limit >= RESOLVE:
                # Найдена новая сущность
                found_entities.update(pre_entities)
                pre_entities = {}
                print("+", found_entities)
                index = index + count - 1
                count = 1
            else:
                index += 1  # Переходим к следующему слову
            limit = LIMIT

        else:
            # Добавленное слово улучшило показатель совпадения сущности
            limit = best
            pre_entities = temp_entities
            count += 1

    # Цикл проверки фразы завершен
    if limit >= RESOLVE:
        # Найдена новая сущность
        found_entities.update(pre_entities)
        print("+", found_entities)

    """Если найденная сущность имеет после себя число - это может быть адресом, как Тутаринова 12.
    Тутаринова - это остановка или улица и она является сущностью, но в данном контексте ее 
    нужно рассматривать как адрес. Поэтому удалим из списка сущностей, те, которые могут быть адресами.
    """
    words = remove_similar_words(words, ["номер"])


    print("Ответ:", found_entities)
    return list(found_entities.keys())


# 8 школа дом 146 квартира 55 улица 18 дом автобус 25 едет в 3 школу
# восьмая школа дом сто сорок шесть квартира пятьдесят пять улица восемнадцать дом автобус двадцать пятый едет в третью школу
#
# алиса маршрут номер 256 улица ленина 158 на 3 автобусе дом культуры 11
# алиса маршрут номер двести пятьдесят шесть улица ленина сто пятьдесят восемь на третьем автобусе дом культуры одиннадцать