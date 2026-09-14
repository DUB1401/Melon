import sys
from typing import TYPE_CHECKING, Literal, NoReturn, overload

import orjson

from dublib.cli.progress_indicator import ProgressIndicator
from dublib.cli.templates.bus import GenerateMessage, MessagesTypes
from dublib.cli.text_styler import get_styled_text_from_html

from .portals import Portals
from .templates import Templates

if TYPE_CHECKING:
	from ....core.system_objects import SystemObjects

#==========================================================================================#
# >>>>> ОСНОВНОЙ КЛАСС <<<<< #
#==========================================================================================#

class Printer:
	"""Оператор вывода."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def progress_indicator(self) -> ProgressIndicator:
		"""Терминальный индикатор прогресса на основе OSC 9;4."""

		return self.__ProgressIndicator

	@property
	def system_objects(self) -> "SystemObjects":
		"""Коллекция системных объектов."""

		return self.__SystemObjects

	@property
	def templates(self) -> Templates:
		"""Расширенные шаблоны вывода."""

		return self.__Templates

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, system_objects: "SystemObjects"):
		"""
		Оператор вывода.

		:param system_objects: Коллекция системных объектов.
		:type system_objects: SystemObjects
		"""
		
		self.__SystemObjects = system_objects

		self.__ProgressIndicator = ProgressIndicator()
		self.__Templates = Templates(self)

	def emit(self, text: str, message_type: MessagesTypes | None = None, origin: str | None = None, end_line: bool = True, flush: bool = False, parse_html: bool = True):
		"""
		Отправляет сообщение в поток вывода.

		:param text: Текст сообщения.
		:type text: str
		:param message_type: Тип сообщения.
		:type message_type: MessagesTypes | None
		:param origin: Источник сообщения.
		:type origin: str | None
		:param end_line: Указывает, нужно ли добавить в конец строки символ новой строки.
		:type end_line: bool
		:param flush: Переключает вывод кэшированных данных.
		:type flush: bool
		:param parse_html: Указывает, парсить HTML теги при помощи функции `get_styled_text_from_html()`.
		:type parse_html: bool
		"""

		if parse_html: text = get_styled_text_from_html(text)
		MessageText = GenerateMessage(text, message_type, origin)
		print(MessageText, end = "\n" if end_line else "", flush = flush)

	def get_parser_portals(self, parser_name: str) -> Portals:
		"""
		Возвращает порталы вывода парсера.

		:param parser_name: Имя парсера.
		:type parser_name: str
		:return: Порталы вывода парсера.
		:rtype: Portals
		"""

		return Portals(self, parser_name)

	#==========================================================================================#
	# >>>>> ШАБЛОНЫ ВЫВОДА БАЗОВЫХ ТИПОВ СООБЩЕНИЙ <<<<< #
	#==========================================================================================#

	@overload
	def critical(self, text: str, origin: str | None = None, end_work: Literal[True] = ...) -> NoReturn: ...
	@overload
	def critical(self, text: str, origin: str | None = None, end_work: Literal[False] = False): ...

	def critical(self, text: str, origin: str | None = None, end_work: bool = False):
		"""
		Выводит в терминал критическую ошибку.

		:param text: Текст сообщения.
		:type text: str
		:param origin: Источник сообщения.
		:type origin: str | None
		:param end_work: Указывает, нужно ли завершить работу скрипта при обработке ошибки.
		:type end_work: bool
		"""

		self.emit(text, MessagesTypes.Critical, origin)
		if end_work: sys.exit(1)

	def debug(self, text: str, origin: str | None = None):
		"""
		Выводит в терминал сообщение отладки.

		:param text: Текст сообщения.
		:type text: str
		:param origin: Источник сообщения.
		:type origin: str | None
		"""

		if self.__SystemObjects.options.DEBUG:
			self.emit(text, MessagesTypes.Debug, origin)

	def error(self, text: str, origin: str | None = None):
		"""
		Выводит в терминал ошибку.

		:param text: Текст сообщения.
		:type text: str
		:param origin: Источник сообщения.
		:type origin: str | None
		"""

		self.emit(text, MessagesTypes.Error, origin)

	def json(self, data: dict):
		"""
		Выводит в терминал JSON-строку.

		:param data: Словарь для преобразования в JSON-строку.
		:type data: dict
		"""

		self.emit(orjson.dumps(data).decode())

	def warning(self, text: str, origin: str | None = None):
		"""
		Выводит в терминал предупреждения.

		:param text: Текст сообщения.
		:type text: str
		:param origin: Источник сообщения.
		:type origin: str | None
		"""

		self.emit(text, MessagesTypes.Warning, origin)