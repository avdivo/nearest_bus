"""
База данных проекта:
BusStop - автобусные остановки
    1. name - название
    2. external_id - внешний id остановки, на сайте Миноблавтотранс https://gpmopt.by/mopt/Home/Index/sluck#/routes/bus
    3. finish - конечная остановка - True, или нет - False
    4. con_a - связь многие-ко-многим от этой остановки к конечным (по направлению движения)
    5. con_b - связь многие-ко-многим к этой остановки от конечных (по направлению движения)

Bus - автобусы (номера)
    1. number - цифро-буквенное обозначение
    2. station - связь многие-ко-многим c остановками на которых автобус может начинать и заканчивать движение
    3. active - работает ли автобус True/False

Router - маршруты следования автобусов. Название маршрута складывается из начальной и конечно остановок через тире.
    1. start - начало маршрута. Один-к-одному
    2. end - конец маршрута. Один-к-одному
    3. bus - номер автобуса

Order - порядок остановок в маршруте
    1. order_number - порядковый номер остановки в маршруте
    2. router - маршрут много-к-одному
    3. bus_stop - остановка много-к-одному

Schedule - расписание
    1. day - день недели (1-7)
    2. bus_stop - связь много-к-одному с автобусной остановкой
    3. bus - связь много-к-одному с автобусом
    4. time - время. Значение в формате Time H:M.

"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# logger = logging.getLogger('django')


class BusStop(models.Model):
    """Автобусные остановки"""
    name = models.CharField(verbose_name='Название', max_length=100)
    external_id = models.CharField(verbose_name='id Миноблавтотранс', max_length=10, unique=True)  # Поле article WB
    finish = models.BooleanField(verbose_name='Это конечная остановка')
    con_a = models.ManyToManyField('self', verbose_name='С этой остановки на какие конечные')
    con_b = models.ManyToManyField('self', verbose_name='На эту остановку с каких конечных')

    def __str__(self):
        word = 'Остановка'
        if self.finish:
            word = 'Конечная остановка'
        return str(f'{word} {self.name}')

    class Meta:
        verbose_name = 'Остановка'
        verbose_name_plural = 'Остановки'


class Bus(models.Model):
    """Автобусы"""
    number = models.CharField(verbose_name='Номер', max_length=10)
    station = models.ManyToManyField(BusStop, verbose_name='Конечные остановки автобуса',
                                     related_name='buses', blank=False)
    active = models.BooleanField(verbose_name='Автобус ходит', default=True)

    def __str__(self):
        return str(f'Автобус №{self.number}')

    class Meta:
        verbose_name = 'Автобус'
        verbose_name_plural = 'Автобусы'


class Router(models.Model):
    """Маршруты следования автобусов"""
    start = models.ForeignKey(BusStop, verbose_name='Начало маршрута', related_name='routers_start',
                              on_delete=models.PROTECT, null=False, blank=False)
    end = models.ForeignKey(BusStop, verbose_name='Конец маршрута', related_name='routers_end',
                            on_delete=models.PROTECT, null=False, blank=False)
    bus = models.ForeignKey(Bus, verbose_name='Автобус', related_name='routers',
                            on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return f'Автобус {self.bus} {self.start.name} - {self.end.name}'

    class Meta:
        verbose_name = 'Маршрут'
        verbose_name_plural = 'Маршруты'


class Order(models.Model):
    """Порядок остановок на маршруте."""
    order_number = models.IntegerField(verbose_name='Номер по-порядку')
    router = models.ForeignKey(BusStop, verbose_name='Маршрут', related_name='orders_for_router',
                               on_delete=models.CASCADE, null=False, blank=False)
    bus_stop = models.ForeignKey(BusStop, verbose_name='Остановка',
                                 on_delete=models.CASCADE, null=False, blank=False)

    def save(self, *args, **kwargs):
        """Автоматическое присвоение порядкового номера для остановки в маршруте
        если он не задан.
        Если это первая запись в маршруте - она получает значение 1."""
        if not self.order_number:
            max_order_number = Order.objects.filter(
                router=self.router, bus_stop=self.bus_stop).order_by('-order_number').first()
            if max_order_number:
                self.order_number = max_order_number.order_number + 1
            else:
                self.order_number = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return str(f'Остановка {self.bus_stop.name} на маршруте {self.router}')

    class Meta:
        verbose_name = 'Остановка по порядку'
        verbose_name_plural = 'Остановки по порядку'


class Schedule(models.Model):
    """Расписание. Временные метки"""
    day = models.IntegerField(verbose_name='День недели',
                              validators=[MinValueValidator(1), MaxValueValidator(7)], default=1)
    bus_stop = models.ForeignKey(BusStop, verbose_name='Остановка', related_name='time_for_bus_stop',
                                 on_delete=models.CASCADE, null=False, blank=False)
    bus = models.ForeignKey(Bus, verbose_name='Автобус', related_name='time_for_bus',
                            on_delete=models.CASCADE, null=False, blank=False)
    time = models.TimeField(verbose_name='Время')

    def get_day_string(self, day_as_int: int):
        """Возвращает сокращенное название дня недели в зависимости от номера.
        Принимает номер дня в неделе."""
        if day_as_int < 1 or day_as_int > 7:
            raise 'Не правильный номер дня недели.'
        days = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
        return days[day_as_int-1]

    def __str__(self):
        return str(f"{self.get_day_string(self.day)} {self.time.strftime('%H:%M')} "
                   f"автобус {self.bus.number} на остановке {self.bus_stop.name}")

    class Meta:
        verbose_name = 'Время'
        verbose_name_plural = 'Время'
