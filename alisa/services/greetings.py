import random

from alisa.models import AlisaUser
from nb.services.AI.openrouter import query_openrouter

from .functions import date_now


def greetings(user: AlisaUser) -> str:
    """
    Приветствие пользователю для новой сессии.
    Выясняет, наступил ли новый день, если да, здоровается.
    Спрашивает пользователя различными способами о направлении:
    если пользователь не имеет имени - вероятно он новый,
    вопрос задается прямо. У бывалых, с именем, можно разнообразить вопрос.

    Args:
        user - объект пользователя

    Return:
        Строка с приветствием и вопросом.
    """
    created_at = getattr(
        user, "previous_last_update", user.last_update
    )  # Когда был последний раз
    user_name = user.user_name  # Обращение к пользователю
    date = date_now()  # Текущее время, дата
    hello = ""

    if created_at and date.date() != created_at.date():
        # Наступил новый день
        hour = date.hour
        if 5 <= hour < 12:
            part_of_day = "утро"
        elif 12 <= hour < 18:
            part_of_day = "день"
        elif 18 <= hour < 23:
            part_of_day = "вечер"
        else:
            part_of_day = "ночь"

        # Для постоянных пользователей с именем произносим его
        if user_name:
            insert_name = f" {user_name}"
        else:
            insert_name = ""

        # Пробуем получить приветствие от ИИ
        hello = query_openrouter(
            prompt_name="greetings",
            prompt_suffix=(
                f"Сейчас {part_of_day}\n"
                f"{f'Пользователь {user_name}' if user_name else ''}"
            ),
        )

        if not hello:
            # Приветствие не получено, используем заготовки
            if part_of_day == "утро":
                hello = random.choice(
                    [
                        f"С новым днём{insert_name}!",
                        f"Доброе утро{insert_name}!",
                        f"Утро доброе{insert_name}!",
                        f"Доброго утречка{insert_name}!",
                        f"Привет{insert_name}!",
                    ]
                )
            if part_of_day == "день":
                hello = random.choice(
                    [
                        f"День добрый{insert_name}!",
                        f"Добрый день{insert_name}!",
                        f"Доброго дня{insert_name}!",
                        f"Привет{insert_name}!",
                        f"Приветик{insert_name}!",
                    ]
                )
            if part_of_day == "вечер":
                hello = random.choice(
                    [
                        f"Вечер добрый{insert_name}!",
                        f"Добрый вечер{insert_name}!",
                        f"Доброго вечера{insert_name}!",
                        f"Привет{insert_name}!",
                        f"Приветик{insert_name}!",
                    ]
                )
            if part_of_day == "ночь":
                hello = random.choice(
                    [
                        f"Доброй ночи{insert_name}!",
                        f"Приветствую{insert_name}, хоть и ночь на дворе!",
                        f"Слушаю{insert_name}, я и ночью тут!",
                        f"Привет{insert_name}, люблю ночные поездки!",
                        f"Приветик{insert_name}! Тихая ночь, свободные дороги.",
                    ]
                )

    if user_name:
        # Если имя произнесено в приветствии, то больше не нужно
        if hello:
            insert_name = ""
            hello += "\n"
        else:
            insert_name = f", {user_name}"

        # Для постоянных пользователей, имеющих имя
        hello += random.choice(
            [
                f"Какой маршрут тебя интересует{insert_name}?",
                f"Я тут{insert_name}, откуда и куда едешь теперь?",
                f"Вижу ты снова в путь{insert_name}! Слушаю.",
                f"Откуда и куда на этот раз{insert_name}?",
                f"Откуда и куда держим курс сейчас{insert_name}?",
                f"Откуда стартуем и куда на сей раз{insert_name}?",
                f"Едем снова{insert_name}? Только скажи откуда и куда.",
                f"Я ждала тебя{insert_name}! Выбирай направление.",
            ]
        )
    else:
        if hello:
            hello += "\n"
        hello += "Откуда и куда вы хотите ехать?"

    return hello
