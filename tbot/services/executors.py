# Классы для выполнения действий в окне чата.
# Изменение параметров, выбор опций...


class Executor:
    """Базовый класс для выполнения действий в окне чата."""
    def __init__(self, bot, chat_id, message_id, text):
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
        self.text = text

    def execute(self):
        """Выполняет действие. В классах - наследниках переопределяется."""
        pass


