"""Legacy compatibility module.

Основная механика звонков удалена и заменена на игру знакомства.
Этот сервис оставлен как безопасная заглушка для обратной совместимости импортов.
"""


class MeetingService:  # pragma: no cover
    def __init__(self, *args, **kwargs) -> None:
        pass
