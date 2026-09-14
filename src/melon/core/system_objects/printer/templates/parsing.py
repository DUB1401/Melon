from typing import TYPE_CHECKING

from dublib.cli.text_styler import FastStyler
from dublib.functions.data import stringify_float

from ._base import _BaseTemplatesSection

if TYPE_CHECKING:
	from .....core.base.formats.base_format.chapter import BaseChapter
	from .....core.base.formats.base_format.data import BaseTitleData
	from .....core.base.formats.base_format.structs import SavingResult

class ParsingTemplates(_BaseTemplatesSection):
	"""Расширенные шаблоны вывода: процесс парсинга."""

	def amending_end(self, amended_chapter_count: int):
		"""
		Шаблон сообщения: дополнение глав завершено.

		:param amended_chapter_count: Количество дополненных глав.
		:type amended_chapter_count: int
		"""

		Text = f"Amended chapters count: {amended_chapter_count}."
		self.printer.emit(Text)
	
	def chapter_amended(self, chapter: "BaseChapter", message: str | None = None):
		"""
		Шаблон сообщения: глава дополнена.

		:param chapter: Данные главы.
		:type chapter: BaseChapter
		:param message: Дополнительное необязательное сообщение о получении главы.
		:type message: str | None
		"""

		if message is None: message = ""
		if message: message = " " + message.strip()

		ChapterNote = "Paid chapter" if chapter.is_paid else "Chapter"
		Text = f"{ChapterNote} {chapter.id} amended.{message}"
		self.printer.emit(Text)

	def chapter_repaired(self, chapter: "BaseChapter"):
		"""
		Шаблон сообщения: глава восстановлена.

		:param chapter: Данные главы.
		:type chapter: BaseChapter
		"""

		ChapterNote = "Paid chapter" if chapter.is_paid else "Chapter"
		Text = f"{ChapterNote} {chapter.id} repaired."
		self.printer.emit(Text)

	def progress(self, index: int, count: int):
		"""
		Шаблон вывода: прогресс парсинга тайтлов.

		:param index: Индекс обрабатываемого тайтла.
		:type index: int
		:param count: Количество тайтлов.
		:type count: int
		"""

		Number = index + 1
		Progress = round(Number / count * 100, 2)
		NumberString = FastStyler(str(Number)).colorize.magenta
		ProgressString = stringify_float(Progress)
		ProgressString = FastStyler(ProgressString + "%").colorize.cyan

		self.printer.progress_indicator.set_progress(Progress)
		self.printer.emit(f"[{NumberString} / {count} | {ProgressString}] ", end_line = False, flush = True)

	def saving_result(self, result: "SavingResult"):
		"""
		Шаблон сообщения: выполнено сохранение тайтла.

		:param result: Результат сохранения тайтла.
		:type result: SavingResult
		"""

		if result.is_slug_changed:
			self.printer.emit("Title slug changed.")

		if result.is_saved: self.printer.emit("Saved.")
		else: self.printer.emit("No changes. Saving skipped.")

		if result.is_local_file_renamed:
			self.printer.emit("File renamed by new slug.")

		if result.unused_images_removed:
			self.printer.emit(f"Removed {result.unused_images_removed} unused images.")

	def start(self, title_data: "BaseTitleData", index: int, titles_count: int):
		"""
		Шаблон сообщения: парсинг начат.

		:param title_data: Данные тайтла.
		:type title_data: BaseTitle
		:param index: Индекс текущей операции парсинга.
		:type index: int
		:param titles_count: Количество тайтлов.
		:type titles_count: int
		"""

		NoteID = f" (ID: {title_data.id})" if title_data.id else ""

		if titles_count > 1:
			self.progress(index, titles_count)

		self.printer.emit(f"Parsing <b>{title_data.slug}</b>{NoteID}…")

	def summary(self, parsed: int, not_found: int, errors: int):
		"""
		Шаблон вывода: результат парсинга.

		:param parsed: Количество успешно собранных тайтлов.
		:type parsed: int
		:param not_found: Количество не найденных в источнике тайтлов.
		:type not_found: int
		:param errors: Количество ошибок.
		:type errors: int
		"""

		self.printer.emit("===== SUMMARY =====")
		Parsed = FastStyler(str(parsed)).colorize.green if parsed else FastStyler(str(parsed)).colorize.red
		NotFound = FastStyler(str(not_found)).colorize.yellow if not_found else FastStyler(str(not_found)).colorize.green
		Errors = FastStyler(str(errors)).colorize.red if errors else FastStyler(str(errors)).colorize.green

		self.printer.progress_indicator.end()
		self.printer.emit(f"Parsed: {Parsed}. Not found: {NotFound}. Errors: {Errors}.")
