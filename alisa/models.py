import json

from django.db import models

from tbot.models import BotUser


class AlisaUser(models.Model):
    """Таблица связывает аккаунты Телеграмм бота с устройствами Алисы."""
    user = models.ForeignKey(BotUser, null=True, on_delete=models.SET_NULL, verbose_name='Пользователь')
    application_id = models.CharField(verbose_name='Идентификатор приложения с Алисой', max_length=100)
    parameters = models.TextField(verbose_name='Память приложения в JSON', default='{}')
    last_update = models.DateTimeField(verbose_name='Последнее обновление', default=None, blank=True, null=True)
    action_count = models.IntegerField(verbose_name='Количество всех действий', default=0)
    schedule_count = models.IntegerField(verbose_name='Количество запросов расписаний', default=0)

    @ staticmethod
    def authorize(application_id):
        """Метод для авторизации пользователя по application_id."""
        user = AlisaUser.objects.filter(application_id=application_id).first()
        return user

    def get_parameters(self, name: str = None):
        """Возвращает запрошенный аттрибут как значение (str);
        Словарь со всеми параметрами, если имя не указано;
        None, если запрошенного аттрибута нет в словаре.
        Принимает имя параметра."""
        addition = json.loads(self.parameters, parse_float=str)
        out = None
        if name is None:
            out = addition
        elif name in addition:
            out = addition.get(name)
        return out

    def set_parameters(self, value, name: str = None):
        """Обновляет указанный параметр или создает новый.
        Принимает значение параметра и имя.
        Если имя не указано, то считает что передан словарь и обновляет все параметры.
        """
        addition = json.loads(self.parameters, parse_float=str)
        if name is None:
            addition = value
        else:
            addition.update({name: value})
        self.parameters = json.dumps(addition, ensure_ascii=False)
        self.save()

    def del_parameters(self, name: str):
        """Удаляет указанный параметр или все, если имя не указано.
        Принимает имя атрибута."""
        additions = json.loads(self.parameters, parse_float=str)
        if name is None:
            additions = {}
        elif name in additions:
            del additions[name]
        self.parameters = json.dumps(additions, ensure_ascii=False)
        self.save()

    def __str__(self):
        return str(f'{self.user}')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
