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
import json

from django.db import models
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator, MaxValueValidator

from utils.translation import get_day_string
from tbot.services.functions import date_now


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
        'buses': список автобусов от 1 ко 2, },
        "stops": {остановка (obj): {автобусы (obj)}}"""
        # Получаем списки остановок назначения, которые находятся рядом.
        # Чтобы учесть маршруты, которые могут идти не на указанную остановку,
        # а на расположенную рядом.
        list_names = [
            json.loads(obj.list_name)
            for obj in StopGroup.objects.all()
        ]

        # Если целевая остановка есть в группе, добавляем все остановки группы
        # в список остановок назначения
        target_stops = set([two])
        for list_name in list_names:
            if two in list_name:
                target_stops.update(list_name)
        target_stops = list(target_stops)  # Список остановок назначения (str)

        # Получаем маршруты, которые проходят через указанную остановку отправления
        routers_one = set(Router.objects.filter(
            Q(start__name=one) |  # остановка - начало маршрута
            Q(end__name=one) |  # остановка - конец маршрута
            Q(orders_for_router__bus_stop__name=one)  # остановка в списке Order
        ).distinct())

        # Получаем маршруты, которые проходят через указанные остановки прибытия
        routers_two = set()
        if target_stops:
            # Если эта остановка в группе, добавляем всю группу
            for stop in target_stops:
                routers = list(Router.objects.filter(
                    Q(start__name=stop) |  # остановка - начало маршрута
                    Q(end__name=stop) |  # остановка - конец маршрута
                    Q(orders_for_router__bus_stop__name=stop)  # остановка в списке Order
                ).distinct())
                routers_two.update(routers)
        else:
            routers_two = set(Router.objects.filter(
                    Q(start__name=two) |  # остановка - начало маршрута
                    Q(end__name=two) |  # остановка - конец маршрута
                    Q(orders_for_router__bus_stop__name=two)  # остановка в списке Order
                ).distinct())

        # Находим пересечение маршрутов.
        # Те маршруты которые есть как в отправлении так и в прибытии
        common_routers = list(routers_one.intersection(routers_two))
        # Перебираем маршруты и находим те, в котором у первой остановки номер по порядку
        # в Order меньше чем у второй остановки. Получаем ее id. Возвращаем объект остановки.

        # Есть случаи, когда на целевую остановку идет автобус с 2-х,
        # расположенных через дорогу (в разные стороны) с одним названием (Чехова, Автобус №7)
        start = set()  # Объекты начальной остановки, может быть 2
        stop = None  # Объект конечной остановок
        buses = set()  # Список автобусов на маршруте между заданными остановками
        stops_bus = {}  # Словарь {остановка (obj): {автобусы (obj)}}
        for router in common_routers:
            # Порядковые номера остановок на маршруте
            order_one = Order.objects.filter(router=router, bus_stop__name=one).first()

            # Для каждой остановки прибытия (str)
            for arrival_stop in target_stops:
                # Порядковые номера остановок на маршруте
                order_two = Order.objects.filter(router=router, bus_stop__name=arrival_stop).first()
                if order_two is None or order_one.order_number > order_two.order_number:
                    continue  # Пропускаем маршруты с направлением обратным нужному

                print(router, " -------------------- ",arrival_stop)

                # Если хоть раз сюда попал, остановка отправления будет определена
                start.add(order_one.bus_stop)  # Получаем объект остановки отправления

                # Для остановок назначения приоритет имеет та, которая была передана
                # в функцию, поэтому проверяем наличие ее в маршруте.
                bus_stop_obj = order_two.bus_stop  # Получаем объект остановки отправления
                if two == arrival_stop:
                    # Получаем объект остановки
                    stop = bus_stop_obj  # Записываем объект остановки прибытия

                buses.add(router.bus)  # Маршрут идет в нужном направлении, записываем его автобус
                # Добавляем остановку и маршрут в словарь
                if bus_stop_obj not in stops_bus:
                    stops_bus[bus_stop_obj] = set()
                stops_bus[bus_stop_obj].add(router.bus)

        if start and stop is None:
            # Если не идентифицирована остановка
            # прибытия пытаемся подобрать другую
            stop = max(stops_bus, key=lambda k: len(stops_bus[k]))


        print("Из функции ", {'start': start, 'finish': stop, 'buses': buses, 'stops': stops_bus})
        return {'start': start, 'finish': stop, 'buses': buses, 'stops': stops_bus}

    def get_bus_by_stop(self):
        """Возвращает список автобусов, проходящих через остановку.
        Принимает объект остановки.
        """
        orders = Order.objects.filter(bus_stop=self)
        buses = {order.router.bus for order in orders}
        return buses

    @staticmethod
    def get_all_bus_stops_names():
        """Возвращает список имен всех остановок в алфавитном порядке, без повторов."""
        stops = set()
        for stop in BusStop.objects.all():
            stops.add(stop.name)
        return sorted(list(stops))

    def __str__(self):
        word = 'Остановка'
        if self.finish:
            word = 'Конечная остановка'
        return str(f'{word} {self.name}')

    class Meta:
        verbose_name = 'Остановка'
        verbose_name_plural = 'Остановки'


class OptionsForStopNames(models.Model):
    """Варианты названий остановок"""
    name = models.CharField(verbose_name='Название', max_length=100)
    options = models.TextField(verbose_name='Вариант названия (список)', default='[]')

    @staticmethod
    def get_dict_options_name():
        table = OptionsForStopNames.objects.all()
        options = {}
        for row in table:
            options[row.name] = json.loads(row.options)
        return options

    def __str__(self):
        return str(f'{self.name} {self.options}')

    class Meta:
        verbose_name = 'Вариант названия автобусной остановки'
        verbose_name_plural = 'Варианты названий автобусных остановок'


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
        now_date = date_now().date()  # Получаем datetime в текущем часовом поясе
        # Есть ли дата в списке праздников
        try:
            day = Holiday.objects.get(date=now_date).day
        except ObjectDoesNotExist:
            day = None
        return day

    def __str__(self):
        return str(f"{self.date} {self.name}")

    class Meta:
        verbose_name = 'Праздник'
        verbose_name_plural = 'Праздники'


# Группировка для остановок прибытия,
# чтобы можно было указать группу остановок,
# куда еще можно поехать, чтобы попасть в нужное место.
class StopGroup(models.Model):
    """Группы остановок. Хранят остановки в json
    [name1, name2, ...]"""

    list_name = models.CharField('Остановки', max_length=100)

    class Meta:
        verbose_name = 'Группа остановок назначения'
        verbose_name_plural = 'Группы остановок назначения'
