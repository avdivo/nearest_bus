import re
from functools import cmp_to_key


def compare_name(a: str, b: str) -> int:
    """
    Сравнивает 2 имени для порядка сортировки.
    :param: a - первый аргумент
    :param: b - второй аргумент
    :return: int - 1 (первый больше), 0 (равны), -1 (первый меньше)
    """
    # Извлекаем имена из строк
    name_a = a.split('_')[0]
    name_b = b.split('_')[0]

    # Разделяем числовую и буквенную части
    name_a = re.findall(r'\d+|[^\d]+', name_a)
    name_b = re.findall(r'\d+|[^\d]+', name_b)

    num_a = int(name_a[0])
    num_b = int(name_b[0])

    alpha_a = name_a[1] if len(name_a) > 1 else ""
    alpha_b = name_b[1] if len(name_b) > 1 else ""

    # Сравниваем числовые части
    if num_a > num_b:
        return 1
    elif num_a < num_b:
        return -1
    else:
        # Если числовые части равны, сравниваем буквенные
        if alpha_a > alpha_b:
            return 1
        elif alpha_a < alpha_b:
            return -1
        else:
            return 0

def sorted_buses(buses: list or set) -> list:
    """Сортировка списка автобусов как надо."""
    return sorted(buses, key=cmp_to_key(compare_name))
