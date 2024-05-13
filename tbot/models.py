"""База данных телеграмм бота"""
import json
from django.db import models



class BotUser(models.Model):
    """Пользователи приложения."""
    user_name = models.CharField(verbose_name='Имя', max_length=100, default='noname')
    user_login = models.CharField(verbose_name='Логин', max_length=100, default='noname')
    user_id = models.CharField(verbose_name='Идентификатор', max_length=15)
    user_menu = models.CharField(verbose_name='Меню пользователя', max_length=50, default='Главное меню')

    def __str__(self):
        return str(f'{self.user_login}')

    def save(self, *args, **kwargs):
        # Если это новый объект, то создаем связанный объект Parameter
        if not self.pk:
            super(BotUser, self).save(*args, **kwargs)
            Parameter.objects.create(bot_user=self)
        else:
            super(BotUser, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Parameter(models.Model):
    """Параметры выполнения программ.
    Программы - это действия выполняющиеся в окне бота."""
    class_name = models.CharField(verbose_name='Класс (программа)', max_length=100)
    favorites = models.TextField(verbose_name='Избранное в JSON', default='{}')
    addition = models.TextField(verbose_name='Дополнительные параметры в JSON', default='{}')
    bot_user = models.OneToOneField(BotUser, on_delete=models.CASCADE, verbose_name='Пользователь', default=None)

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


class IdsForName(models.Model):
    """Идентификаторы для имен.
    Длинные названия не могут быть использованы в качестве идентификатора кнопки
    в телеграмме. Поэтому используется идентификатор для имени. В таблице хранятся
    имена и их идентификаторы. Для всех пользователей одна таблица.
    """

    name = models.CharField(verbose_name='Имя', max_length=200, unique=True)

    def __str__(self):
        return str(f'{self.name}')

    @staticmethod
    def get_id_by_name(name: str):
        """Возвращает идентификатор по имени.
        Принимает имя.
        Проверяет, если имени нет в таблице, то создает его. Возвращает его идентификатор.
        Если имя уже есть в таблице, то возвращает его идентификатор.
        """
        id_name, created = IdsForName.objects.get_or_create(name=name)
        return str(id_name.id)

    @staticmethod
    def get_name_by_id(id: str):
        """Возвращает имя по идентификатору.
        Принимает идентификатор.
        Проверяет, если идентификатора нет в таблице, то возвращает ошибку.
        Если идентификатор есть в таблице, то возвращает его имя.
        """
        return IdsForName.objects.get(id=id).name

    class Meta:
        verbose_name = 'Идентификатор для имени'
        verbose_name_plural = 'Идентификаторы для имен'