import json

import re
from difflib import SequenceMatcher

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .services.talk_to_alisa import answer_to_alisa







@csrf_exempt
def alisa(request):
    # Эндпоинт для получения запросов от Алисы.
    # Печатаем request.body, чтобы посмотреть, что приходит от Алисы с собдюдением форатирования
    request_body = json.loads(request.body)
    # print(json.dumps(request_body, indent=4, ensure_ascii=False))

    text = answer_to_alisa(request_body)

    answer = {
        "response": {
            "text": text,
            "tts": text,
            # "tts": "Привет, я очень рада что вы, Лена и Вика присоединились к элитной группе кукуренок.",
            "end_session": False,
        },
        "version": "1.0"
    }

    return HttpResponse(json.dumps(answer))


    # return HttpResponse(json.dumps(answer))
# ------------------------------------ перенес
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
        'Социалистическая': ['Социалистическая', 'шанхай', '11 городок'],
        'Суворова': ['Суворова', 'штаны', 'цыганский парк'],
        'Костёл Святого Антония': ['Костёл Святого Антония', 'костел'],
        'Собор Архангела Михаила': ['Собор Архангела Михаила', 'церковь', 'собор', 'Михайловская'],
        'Медиицнский колледж': ['Медиицнский колледж', 'медуха', 'мед', 'медучилище'],
        'Школа № 11': ['Школа 11', '11 школа', '11'],
        'Школа № 9': ['Школа 9', '9 школа'],
        'Мебельная фабрика': ['Мебельная фабрика', 'Санстанция'],
        'Школа № 8': ['Школа 8', '8 школа', '8'],
        'СЭС': ['СЭС', 'Электросети'],
        '14-й городок': ['14-й городок', '14 городок', '14'],
        'Комбинат хлебопродуктов': ['Комбинат хлебопродуктов', 'Мелькомбинат'],
        'РСУ': ['РСУ', 'Ремонтно строительное управление'],
        'Рынок': ['Рынок', 'базар'],
        'Сыродельный комбинат': ['Сыродельный комбинат', 'сыркомбинат'],
        'Школа № 2': ['Школа 2', '2 школа', '2'],
        'Молодёжный центр': ['Молодёжный центр', 'центральный'],
        'АЗС': ['АЗС', 'автозаправка'],
        'Поликлиника': ['Поликлиника', 'больница'],




    }

    def find_matching_stop(phrase, stops_list):
        """Поиск наиболее похожего названия остановки из списка имеющихся.
        Принимает название остановки. Ищет похожие названия из списка и расширенного
        списка для некоторых остановок.
        Возвращает название остановки (правильное, из основного списка) и степень его схожести)."""
        best_match = None
        best_match_ratio = 0

        def name_generator(stops, options):
            """Возвращает имена остановок в преобразованном виде
            (только буквы и цифры в нижнем регистре, ё - заменена на е.
            И оригинальные имена (кортеж).
            Получает список остановок и дополнительный словарь в котором указаны
            варианты названия некоторых остановок {Название: [Вариант1, Вариант2,...]}.
            Если у остановки есть варианты - возвращает их, если нет - только ее."""
            for stop in stops:
                if stop in options:
                    for option in options[stop]:
                        name = option.lower().replace('ё', 'е')
                        name = re.sub(r'\W+', '', name)
                        yield name, stop
                else:
                    name = stop.lower().replace('ё', 'е')
                    name = re.sub(r'\W+', '', name)
                    yield name, stop

        # Перебор всех остановок
        stops_list = name_generator(stops_list, addition)
        for stop, original_name in stops_list:
            similarity_ratio = SequenceMatcher(None, phrase, stop).ratio()
            if similarity_ratio > best_match_ratio:
                best_match = original_name
                best_match_ratio = similarity_ratio

        return best_match, best_match_ratio

    # Пример использования функции
    phrase = "соц"

    words = request_body['request']['nlu']['tokens']
    # Удалить из списка слово номер
    try:
        words.remove('номер')
    except:
        pass

    new_phrase = ''
    mem = []
    best_result = 0
    best_stop = ''
    for word in words:
        matching_stops = find_matching_stop(new_phrase + ' ' + word, stops_list)
        if matching_stops[1] < 0.5:
            continue
        if matching_stops[1] > best_result:
            best_result = matching_stops[1]
            best_stop = matching_stops[0]
            new_phrase += ' ' + word
        elif matching_stops[1] < best_result:
            mem.append(best_stop)  # Этот результат принят
            new_phrase = word
            best_result = 0
            best_stop = ''
            matching_stops = find_matching_stop(new_phrase, stops_list)
            if matching_stops[1] > 0.5:
                best_result = matching_stops[1]
                best_stop = matching_stops[0]
    if best_stop:
        mem.append(best_stop)
    mem = mem[:2]

    print(mem)
    if not mem:
        text = 'Не найдено.'
    else:
        text = ' ,'.join(mem)
# -------------------------------------------------------

    # return HttpResponse(json.dumps(answer_to_alisa(request_body)))


    # raise PermissionDenied
