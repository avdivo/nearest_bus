"""База данных телеграмм бота"""
import json
from django.db import models


class BotUser(models.Model):
    """Пользователи приложения."""
    user_name = models.CharField(verbose_name='Имя', max_length=100)
    user_login = models.CharField(verbose_name='Логин', max_length=100)
    user_id = models.CharField(verbose_name='Идентификатор', max_length=15)
    user_attributes = models.TextField(verbose_name='Аттрибуты в JSON')
    user_menu = models.CharField(verbose_name='Меню пользователя', max_length=50, default='Главное меню')

    def get_user_attr(self, name: str):
        """Возвращает запрошенный аттрибут в виде словаря или None.
        Принимает имя атрибута"""
        attributes = json.loads(self.user_attributes)
        return attributes.get(name)

    def set_user_attr(self, name: str, value):
        """Обновляет указанный аттрибут или создает новый.
        Принимает имя атрибута и значение."""
        attributes = json.loads(self.user_attributes)
        attributes.update({name: value})
        self.user_attributes = json.dumps(attributes)
        self.save()

    def del_user_attr(self, name: str):
        """Удаляет указанный аттрибут.
        Принимает имя атрибута."""
        attributes = json.loads(self.user_attributes)
        if name in attributes:
            del attributes[name]
            self.user_attributes = json.dumps(attributes)
            self.save()

    def __str__(self):
        return str(f'{self.user_login}')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
