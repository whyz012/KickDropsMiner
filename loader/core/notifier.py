import asyncio
import threading
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiohttp import ClientSession # Импортируем ClientSession


class TelegramNotifier:
    """Обрабатывает отправку асинхронных Telegram уведомлений с aiogram 3.0."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.bot = None
        self._session = None # Добавляем для явного управления сессией

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = ClientSession() # Создаем сессию, если ее нет или она закрыта
        return self._session

    async def _send_message_async(self, message: str):
        """Внутренняя асинхронная функция для отправки сообщения."""
        if not self.token or not self.chat_id:
            return

        if self.bot is None:
            try:
                session = await self._get_session()
                self.bot = Bot(
                    token=self.token,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                    session=session, # Передаем явно сессию
                )
            except Exception as e:
                print(f"Ошибка инициализации Telegram бота: {e}")
                return

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
        except Exception as e:
            print(f"Ошибка при отправке Telegram сообщения: {e}")

    async def close(self):
        print(f"TelegramNotifier: Вызван метод close(). self.bot={self.bot}")
        if self._session and not self._session.closed:
            try:
                await self._session.close() # Закрываем явно aiohttp сессию
                print("TelegramNotifier: Сессия aiohttp успешно закрыта.")
            except Exception as e:
                print(f"Ошибка при закрытии сессии Telegram бота: {e}")
        else:
            print("TelegramNotifier: Сессия aiohttp уже закрыта или не инициализирована.")

    def send_notification(self, message: str):
        """Запускает отправку уведомления в отдельном потоке с новым циклом asyncio."""

        def run_asyncio_task():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._send_message_async(message))
            except Exception as e:
                print(f"Ошибка выполнения asyncio/Telegram: {e}")

        # Запускаем в отдельном потоке, чтобы избежать блокировки UI
        threading.Thread(target=run_asyncio_task, daemon=True).start()
