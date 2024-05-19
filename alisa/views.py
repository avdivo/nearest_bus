import json

import re
from difflib import SequenceMatcher

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .services.talk_to_alisa import answer_to_alisa


@csrf_exempt
def alisa(request):
    """Эндпоинт для получения запросов от Алисы."""
    request_body = json.loads(request.body)
    # print(json.dumps(request_body, indent=4, ensure_ascii=False))

    # Если это начало сессии просто приветствие
    new = request_body['session']['new']
    if new:
        text = 'Откуда и куда вы хотите ехать?'
    else:
        text = answer_to_alisa(request_body)

    answer = {
        "response": {
            "text": text,
            "tts": text,
            "end_session": False,
        },
        "version": "1.0"
    }

    return HttpResponse(json.dumps(answer))
