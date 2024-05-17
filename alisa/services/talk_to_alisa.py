# Модуль принимает запросы от сервиса Яндекс.Диалоги и возвращает ответы.
# Реализует функции навыка Слуцкие автобусы.

import re
import json
import logging
from difflib import SequenceMatcher

from alisa.models import AlisaUser

stops_list = ['Индустриальный колледж', 'Тутаринова', 'Сахарный комбинат',
              'Экологический центр', 'Уреченская', 'Дом культуры', 'Кадетское училище',
              '1 Августа', 'Льнозавод', 'Поселковая', 'Суворова', 'Костёл Святого Антония',
              'Автовокзал', 'Автобусный парк № 2', 'Садовый проезд', 'Библиотека',
              'Собор Архангела Михаила', 'Майский посад', 'Медиицнский колледж',
              'Советская', 'Городок', 'Зелёная', 'Микрорайон Северный', 'Дружная',
              'Центр соцобслуживания', 'Школа № 11', 'Автовокзал *', 'Медицинский колледж',
              'Лучники (школа)', 'Школа № 9', 'Копыльская', 'Центральная', 'Юбилейная',
              'Мебельная фабрика', 'Аптека № 80', 'Школа № 8', 'СЭС', 'Слуцкие Пояса',
              'Борисовца', 'Ивановского', 'Любанская', '14-й городок', 'Спасская',
              'Минская', 'Микрорайон Новодворцы', 'Комбинат хлебопродуктов', 'Мясокомбинат',
              'Чехова', 'Геологоразведка', 'РСУ', 'Рынок', 'Сыродельный комбинат',
              'Социалистическая', 'Торговый центр', 'Кольцевая', 'Школа № 2',
              'Проектный институт', 'Молодёжный центр', 'Лучники-1', 'Водоканал',
              'Крановый завод', 'Лучники (центр)', 'Хлебозавод', 'Типография', 'Гастелло',
              'Пушкина', 'Зеленхоз', 'АЗС', 'Автобусный парк № 2 ОАО МОАТ', 'Гаспадарчая',
              'ДОСААФ', 'Поликлиника', 'Водоканал *', 'ССК', 'Магазин стройматериалов',
              'Магистральная']

addition = {
    'Дом культуры': ['Дом культуры', 'дк'],
    'Социалистическая': ['Социалистическая', 'шанхай', 'одиннадцатый городок'],
    'Суворова': ['Суворова', 'штаны', 'цыганский парк'],
    'Костёл Святого Антония': ['Костёл Святого Антония', 'костел'],
    'Собор Архангела Михаила': ['Собор Архангела Михаила', 'церковь', 'собор', 'Михайловская'],
    'Медиицнский колледж': ['Медиицнский колледж', 'медуха', 'мед', 'медучилище'],
    'Школа № 11': ['Школа номер одиннадцать', 'одиннадцатая школа', 'одиннадцать'],
    'Школа № 9': ['Школа номер девять', 'девятая школа'],
    'Мебельная фабрика': ['Мебельная фабрика', 'Санстанция'],
    'Аптека № 80': ['Аптека номер восемьдесят', 'восьмидесятая аптека', 'восемьдесят'],
    'Школа № 8': ['Школа номер восемь', 'восьмая школа', 'восемь'],
    'СЭС': ['СЭС', 'Электросети'],
    '14-й городок': ['четырнадцатый городок', 'четырнадцать'],
    'Комбинат хлебопродуктов': ['Комбинат хлебопродуктов', 'Мелькомбинат'],
    'РСУ': ['РСУ', 'Ремонтно строительное управление'],
    'Рынок': ['Рынок', 'базар'],
    'Сыродельный комбинат': ['Сыродельный комбинат', 'сыркомбинат'],
    'Школа № 2': ['Школа номер два', 'вторая школа', 'два'],
    'Молодёжный центр': ['Молодёжный центр', 'центральный'],
    'АЗС': ['АЗС', 'автозаправка'],
    'Поликлиника': ['Поликлиника', 'больница'],

}


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


def find_matching_stop(word, anything_list, add_dict):
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
    stops_list = name_generator(anything_list, addition)  # Получаем очередную сущность
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
    # Получаем текст в чистом виде (цифры - словами)
    words = request_body['request']['original_utterance']
    out = select_samples_by_phrase(words, stops_list, addition)
    if not out:
        return 'Ничего не найдено.'
    if len(out) == 1:
        return f'Остановка: {out[0]}'
    return f'Маршрут: {" ,".join(out)}'


    application_id = request['session']['application']['application_id']
    user = AlisaUser.authorize(application_id)
    if user is None:
        text = ('Здравствуйте. Я подскажу вам, какие автобусы проходят в ближайшее время '
                'на выбранной вами остановке в Слуцке. Обратите внимание, для работы мне '
                'нужен доступ к вашим данным в телеграмм боте "Ближайший автобус в Слуцке". '
                'Вам необходимо войти в бот, выбрать в меню "Связь с Алисой" и написать '
                'Парольную фразу, по которой я вас узнаю. Сообщите мне эту парольную фразу.' )
        return {
            "response": {
                "text": text,
                "tts": text,
                "end_session": False
            },
            "session_state": {
                "value": "authorize"
            },
            "version": "1.0"
        }

    what_can_you_do = ('Я подскажу вам, какие автобусы проходят в ближайшее время '
                       'на выбранной вами остановке в Слуцке. '
                       'Назовите маршрут и я сообщу вам время прибытия ближайших автобусов.')
    help_text = ('Чтобы услышать список маршрутов скажите "Маршруты".'
                 'Назовите маршрут, чтобы узнать время прибытия ближайших автобусов на остановку.'
                 'Для получения информации о следующем автобусе скажите "Следующий".')