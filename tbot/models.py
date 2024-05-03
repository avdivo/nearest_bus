"""База данных телеграмм бота"""
import json
from django.db import models


class BotUser(models.Model):
    """Пользователи приложения."""
    user_name = models.CharField(verbose_name='Имя', max_length=100)
    user_login = models.CharField(verbose_name='Логин', max_length=100)
    user_id = models.CharField(verbose_name='Идентификатор', max_length=15)
    user_menu = models.CharField(verbose_name='Меню пользователя', max_length=50, default='Главное меню')

    def __str__(self):
        return str(f'{self.user_login}')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Parameter(models.Model):
    """Параметры выполнения программ.
    Программы - это действия выполняющиеся в окне бота."""
    class_name = models.CharField(verbose_name='Класс (программа)', max_length=100)
    favorites = models.TextField(verbose_name='Избранное в JSON', default='{}')
    addition = models.TextField(verbose_name='Дополнительные параметры в JSON', default='{}')
    bot_user = models.OneToOneField(BotUser, on_delete=models.CASCADE, verbose_name='Пользователь')

    def get_addition(self, name: str):
        """Возвращает запрошенный аттрибут в виде словаря или None.
        Принимает имя атрибута"""
        addition = json.loads(self.addition)
        return addition.get(name)

    def set_addition(self, name: str, value):
        """Обновляет указанный аттрибут или создает новый.
        Принимает имя атрибута и значение."""
        addition = json.loads(self.addition)
        addition.update({name: value})
        self.addition = json.dumps(addition)
        self.save()

    def del_addition(self, name: str):
        """Удаляет указанный аттрибут.
        Принимает имя атрибута."""
        additions = json.loads(self.addition)
        if name in additions:
            del additions[name]
            self.addition = json.dumps(additions)
            self.save()

    def __str__(self):
        return str(f'{self.name}')

    class Meta:
        verbose_name = 'Дополнительный параметр'
        verbose_name_plural = 'Дополнительные параметры'
