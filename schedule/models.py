"""
База данных проекта:
BusStop - автобусные остановки
    1. name - название
    2. external_id - внешний id остановки, на сайте Миноблавтотранс https://gpmopt.by/mopt/Home/Index/sluck#/routes/bus
    3. finish - конечная остановка - True, или нет - False
    4. con_to - связь многие-ко-многим от этой остановки к конечным (по направлению движения)
    5. con_from - связь многие-ко-многим к этой остановки от конечных (по направлению движения)

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
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator, MaxValueValidator

from utils.translation import get_day_string


# logger = logging.getLogger('django')


class BusStop(models.Model):
    """Автобусные остановки"""
    name = models.CharField(verbose_name='Название', max_length=100)
    external_id = models.CharField(verbose_name='id Миноблавтотранс', max_length=10, unique=True)  # Поле article WB
    finish = models.BooleanField(verbose_name='Это конечная остановка', default=False)
    con_to = models.ManyToManyField('self', verbose_name='С этой остановки на какие конечные', null=True)
    con_from = models.ManyToManyField('self', verbose_name='На эту остановку с каких конечных')

    def get_related_stops(self):
        """Возвращает список остановок, связанных с данной остановкой одним маршрутом.
        Принимает объект остановки.
        Находит все маршруты, в которых есть переданная остановка через Order.
        Возвращает все остановки на этих маршрутах."""
        # Найдем все записи, связанные с остановкой
        related_orders = Order.objects.filter(bus_stop=self)
        # Найдем все маршруты, связанные c этими записями
        related_routers = [order.router for order in related_orders]
        # Найдем все остановки на этих маршрутах
        related_stops = set()
        for router in related_routers:
            stops = Order.objects.filter(router=router).order_by('order_number')
            for stop in stops:
                related_stops.add(stop.bus_stop)

        return related_stops

    @staticmethod
    def get_routers_by_two_busstop(one: str, two: str):
        """Возвращает информацию по маршрутам проходящим через 2 остановки в указанном порядке.
        Принимает 2 названия остановок.
        Возвращает словарь: {'start': объект остановки, 'finish': объект остановки,
        'buses': список автобусов от 1 ко 2}."""
        # Получаем все объекты Order, связанные с каждой из остановок
        orders_one = Order.objects.filter(bus_stop__name=one)
        orders_two = Order.objects.filter(bus_stop__name=two)

        # Получаем маршруты, связанные с каждым из наборов объектов Order
        routers_one = {order.router for order in orders_one}
        routers_two = {order.router for order in orders_two}

        # Находим пересечение маршрутов
        common_routers = routers_one.intersection(routers_two)

        # Перебираем маршруты и находим тот, в котором у первой остановки номер по порядку
        # в Order меньше чем у второй остановки. Получаем ее id. Возвращаем объект остановки.
        #
        start, stop = None, None
        buses = []  # Список автобусов на маршруте между заданными остановками
        for router in common_routers:
            order_one = Order.objects.get(router=router, bus_stop__name=one)
            order_two = Order.objects.get(router=router, bus_stop__name=two)
            if order_one.order_number < order_two.order_number:
                buses.append(router.bus)  # Маршрут идет в нужном направлении, запоминаем его автобус
                start = order_one.bus_stop  # Возвращаем объект остановки
                stop = order_two.bus_stop

        return {'start': start, 'finish': stop, 'buses': buses}

    def get_bus_by_stop(self):
        """Возвращает список автобусов, проходящих через остановку.
        Принимает объект остановки.
        """
        orders = Order.objects.filter(bus_stop=self)
        buses = {order.router.bus for order in orders}
        return buses

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
                                     related_name='buses')
    active = models.BooleanField(verbose_name='Автобус ходит', default=True)

    @staticmethod
    def get_buses(only_active=True):
        """Возвращает список автобусов.
        Принимает параметр вернуть все автобусы, не только активные.
        """
        if only_active:
            return Bus.objects.filter(active=True).values_list('number', flat=True)
        else:
            return Bus.objects.all().values_list('number', flat=True)

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

    def get_stops_by_route(self, route):
        """Возвращает список остановок на маршруте"""
        return Order.objects.filter(router=route).order_by('order_number')

    def __str__(self):
        return f'{self.bus} {self.start.name} - {self.end.name}'

    class Meta:
        verbose_name = 'Маршрут'
        verbose_name_plural = 'Маршруты'


class Order(models.Model):
    """Порядок остановок на маршруте."""
    order_number = models.IntegerField(verbose_name='Номер по-порядку')
    router = models.ForeignKey(Router, verbose_name='Маршрут', related_name='orders_for_router',
                               on_delete=models.CASCADE, null=False, blank=False)
    bus_stop = models.ForeignKey(BusStop, verbose_name='Остановка',
                                 on_delete=models.CASCADE, null=False, blank=False)

    def save(self, *args, **kwargs):
        """Автоматическое присвоение порядкового номера для остановки в маршруте
        если он не задан.
        Если это первая запись в маршруте - она получает значение 1."""
        if not self.order_number:
            max_order_number = Order.objects.filter(
                router=self.router).order_by('-order_number').first()
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

    def __str__(self):
        return str(f"{get_day_string(self.day)} {self.time.strftime('%H:%M')} "
                   f"автобус {self.bus.number} на остановке {self.bus_stop.name}")

    class Meta:
        verbose_name = 'Время'
        verbose_name_plural = 'Время'


class Holiday(models.Model):
    """Переопределяемые дни. Указываем дату, причину и день недели
    которому он будет соответствовать. Например, суббота какой-то даты
    будет рабочей, за прошлый понедельник. Тогда записываем дату этой субботы и
    день недели которым она будет считаться."""
    date = models.DateField(verbose_name='Дата праздника', unique=True)
    name = models.CharField(verbose_name='Название праздника', max_length=100)
    day = models.IntegerField(verbose_name='День недели',
                              validators=[MinValueValidator(1), MaxValueValidator(7)], default=7)

    @staticmethod
    def is_today_holiday():
        """Если дата есть в таблице, возвращает день недели которым она будет считаться."""
        # Определяем текущую дату с поправкой на часовой пояс
        current_timezone = timezone.get_current_timezone()
        utc_time = timezone.now()  # получаем текущую дату в UTC
        date_now = utc_time.astimezone(current_timezone).date()  # конвертируем дату в текущий часовой пояс
        # Есть ли дата в списке праздников
        try:
            day = Holiday.objects.get(date=date_now).day
        except ObjectDoesNotExist:
            day = None
        return day

    def __str__(self):
        return str(f"{self.date} {self.name}")

    class Meta:
        verbose_name = 'Праздник'
        verbose_name_plural = 'Праздники'