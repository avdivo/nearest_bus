# Вспомогательные функции
import telebot

from django.utils import timezone

from tbot.models import BotUser


def date_now():
    """Возвращает текущую дату и время в формате datetime с поправкой на часовой пояс."""
    # Определяем текущую дату с поправкой на часовой пояс
    current_timezone = timezone.get_current_timezone()
    utc_time = timezone.now()  # получаем текущую дату в UTC
    date_now = utc_time.astimezone(current_timezone)  # конвертируем дату в текущий часовой пояс
    return date_now


def authorize(from_user) -> BotUser:
    """Автоматическая регистрация и авторизация пользователя.
    Получает сообщение пользователя. Проверяет по id ТГ есть ли он в БД.
    Если нет - добавляет.
    Возвращает объект модели пользователей.
    Обновляет время последнего входа пользователя и активен ли он.
    """
    if not from_user.is_bot:
        user_id = from_user.id
        user = BotUser.objects.filter(user_id=user_id).first()
        if not user:
            # Добавляем пользователя в БД
            first_name = from_user.first_name if from_user.first_name else "NoName"
            username = from_user.username if from_user.username else "NoLogin"
            user = BotUser.objects.create(user_id=user_id, user_name=first_name, user_login=username)
            user.save()
        user.last_update = date_now()
        user.save()
        return user

    return None


# Выводим 4 кнопки по 2 в строке. Функция keys
def main_menu():
    """Создает клавиатуру с кнопками. Возвращает объект клавиатуры."""
    args = ['Избранное', 'Полное расписание', '', 'Button 4']
    return (telebot.types.ReplyKeyboardMarkup(row_width=2).
            add(*[telebot.types.KeyboardButton(name) for name in args]))

# Функция для вывода в телеграмм 4 Switch-кнопок с цифрами от 1 до 4
