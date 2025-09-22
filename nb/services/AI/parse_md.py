from typing import List, Optional

    
def get_section(markdown_text: str, heading: str, level: int = 1) -> Optional[str]:
    """
    Извлекает содержимое Markdown от указанного заголовка до следующего
    заголовка того же уровня, включая все подзаголовки.

    Параметры
    ----------
    markdown_text : str
        Исходный текст в формате Markdown.
    heading : str
        Текст заголовка, с которого нужно начать извлечение (без символов #).
    level : int, по умолчанию 1
        Уровень заголовка (1 = #, 2 = ##, 3 = ### и т.д.).

    Возвращает
    ----------
    str | None
        Содержимое секции в виде строки или None, если заголовок не найден.
    """
    lines: List[str] = markdown_text.splitlines()
    start_prefix = "#" * level + " "
    end_prefix = start_prefix  # следующий заголовок того же уровня

    inside_section = False
    collected: List[str] = []

    for line in lines:
        if line.startswith(start_prefix):
            # Если мы уже внутри секции и встретили новый заголовок того же уровня — выходим
            if inside_section:
                break
            # Проверяем, что это нужный заголовок
            if line[len(start_prefix):].strip() == heading:
                inside_section = True
                continue
        if inside_section:
            collected.append(line)

    return "\n".join(collected) if collected else None
