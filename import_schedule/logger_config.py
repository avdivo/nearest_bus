import logging
import colorlog

log_colors = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

handler = colorlog.StreamHandler()
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(message)s",
    log_colors=log_colors
)
handler.setFormatter(formatter)

logger = logging.getLogger()  # корневой логгер
logger.setLevel(logging.INFO)

# Чтобы избежать дублирующего вывода, чистим старые обработчики
if not logger.handlers:
    logger.addHandler(handler)
else:
    logger.handlers = [handler]  # если хочешь жёстко перезаписать

# Можно также сделать функцию, если логгер конфигурируется динамически
