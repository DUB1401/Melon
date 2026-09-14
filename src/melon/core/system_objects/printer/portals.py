from typing import TYPE_CHECKING, Literal, NoReturn, overload

from dublib.web_requestor import WebResponse

from ... import exceptions
from ...base.formats.base_format.enums import ImagesTypes

if TYPE_CHECKING:
	from ...base.formats.base_format.chapter import BaseChapter
	from ...base.formats.base_format.controller import BaseTitleController
	from ...base.formats.base_format.data import BaseTitleData
	from . import Printer

class Portals:
	"""Порталы вывода парсера."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def printer(self) -> "Printer":
		"""Оператор вывода."""

		return self.__Printer

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, printer: "Printer", parser_name: str):
		"""
		Порталы вывода парсера.

		:param printer: Оператор вывода.
		:type printer: Printer
		:param parser_name: Имя парсера.
		:type parser_name: str
		"""

		self.__Printer = printer
		self.__ParserName = parser_name

	#==========================================================================================#
	# >>>>> ШАБЛОНЫ ОШИБОК <<<<< #
	#==========================================================================================#

	@overload
	def authorization_required(self, text: str | None = None, exception: Literal[True] = True) -> NoReturn: ...
	@overload
	def authorization_required(self, text: str | None = None, exception: Literal[False] = ...): ...

	def authorization_required(self, text: str | None = None, exception: bool = True):
		"""
		Портал ошибки: требуется авторизация.

		:param text: Описание ошибки. Следует указать краткую инструкцию по авторизации, если таковая поддерживается.
		:type text: str | None
		:param exception: Указывает, выбрасывать ли исключение.
		:type exception: bool
		:raises ParsingError: Активирована опция выброса исключения.
		"""

		if not text:
			text = "Should use authorization method for selected parser."

		self.__Printer.critical(text)

		if exception:
			raise exceptions.parsing.AuthorizationRequired(text)

	@overload
	def request_error(self, response: WebResponse, text: str | None = None, exception: Literal[True] = True) -> NoReturn: ...
	@overload
	def request_error(self, response: WebResponse, text: str | None = None, exception: Literal[False] = ...): ...

	def request_error(self, response: WebResponse, text: str | None = None, exception: bool = True):
		"""
		Портал ошибки: неудачный запрос.

		:param response: Контейнер ответа.
		:type response: WebResponse
		:param text: Описание ошибки.
		:type text: str | None
		:param exception: Указывает, выбрасывать ли исключение.
		:type exception: bool
		:raises ParsingError: Выбрасывается при активации соответствующего аргумента.
		"""

		if not text: text = "Request error."

		Text = f"{text} Response code: {response.status_code}."
		self.__Printer.error(Text)

		if self.printer.system_objects.options.DEBUG and response.json:
			self.printer.debug(str(response.json))

		if exception:
			raise exceptions.parsing.ParsingError(text)

	def unsupported_format(self, title_format: str | None = None, exception: bool = True):
		"""
		Шаблон предупреждения: неподдерживаемый формат JSON.

		:param format: Имя формата.
		:type format: str | Non
		:param exception: Указывает, следует ли выбросить исключение.
		:type exception: bool
		:raises UnsupportedFormat: Выбрасывается при активации соответствующего аргумента.
		"""

		Format = f": \"{title_format}\"" if title_format else ""
		Text = f"Unsupported JSON format{Format}."

		self.__Printer.error(Text)

		if exception:
			raise exceptions.parsers.UnsupportedFormat(Text)

	#==========================================================================================#
	# >>>>> ШАБЛОНЫ ПРЕДУПРЕЖДЕНИЙ <<<<< #
	#==========================================================================================#

	def chapter_not_found(self, chapter: "BaseChapter", exception: bool = True):
		"""
		Портал предупреждения: глава не найдена.

		:param chapter: Данные главы.
		:type chapter: BaseChapter
		:param exception: Указывает, выбрасывать ли исключение.
		:type exception: bool
		:raise ChapterNotFound: Выбрасывается в качестве исключения портала.
		"""

		Text = f"Chapter {chapter.id} not found."
		self.__Printer.error(Text)

		if exception:
			raise exceptions.parsing.ChapterNotFound(chapter.id, chapter.slug)

	def title_not_found(self, title_data: "BaseTitleData", exception: bool = True):
		"""
		Портал предупреждения: тайтл не найден.

		:param title_data: Данные тайтла.
		:type title_data: BaseTitleData
		:param exception: Указывает, следует ли выбросить исключение.
		:type exception: bool
		:raises TitleNotFound: Выбрасывается в качестве исключения портала.
		"""

		NoteID = f" (ID: {title_data.id})" if title_data.id else ""
		Text = f"Title: \"{title_data.slug}\"{NoteID}. Not found."

		self.__Printer.warning(Text)

		if exception:
			raise exceptions.parsing.TitleNotFound(title_data)

	#==========================================================================================#
	# >>>>> ШАБЛОНЫ СООБЩЕНИЙ <<<<< #
	#==========================================================================================#

	def chapter_skipped(self, chapter: "BaseChapter", comment: str | None = None):
		"""
		Портал сообщения: дополнение главы пропущено.

		:param chapter: Данные главы.
		:type chapter: BaseChapter
		:param comment: Комментарий о причине пропуска.
		:type comment: str | None
		"""

		ChapterType = "Paid chapter " if chapter.is_paid else "Chapter "
		ChapterIdentificator = ""

		if chapter.id:
			ChapterIdentificator = str(chapter.id)
		elif chapter.slug:
			ChapterIdentificator = f"\"{chapter.slug}\""

		comment = f" {comment}" if comment else ""
		Text = f"{ChapterType}{ChapterIdentificator} skipped.{comment}"

		self.__Printer.emit(Text)

	def collect_progress_by_page(self, page: int):
		"""
		Портал сообщения: индикация прогресса сбора коллекции.

		:param page: Номер страницы каталога, с которого собраны данные.
		:type page: int
		"""

		self.__Printer.emit(f"Titles on page {page} collected.")

	def covers_unstubbed(self, title: "BaseTitleController[BaseTitleData]"):
		"""
		Портал сообщения: обложки отфильтрованы, так как являются заглушками.

		Также полностью удаляет данные обложек и их директорию.

		:param title: Тайтл.
		:type title: BaseTitleController
		"""

		title.data.clear_covers()
		title.remove_images_type_directory(ImagesTypes.Cover)

		self.__Printer.emit("Stubs detected. Covers data cleared.")