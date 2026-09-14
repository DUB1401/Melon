from abc import ABC
from typing import Sequence

from .....core import exceptions
from .chapter import BaseChapter

class Branch(ABC):
	"""Ветвь контента."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def chapters(self) -> tuple[BaseChapter, ...]:
		"""Последовательность глав."""

		return tuple(self._Chapters.values())

	@property
	def chapters_count(self) -> int:
		"""Количество глав."""

		return len(self._Chapters.values())

	@property
	def empty_chapters_count(self) -> int:
		"""Количество глав без контента."""

		return sum(1 for CurrentChapter in self._Chapters.values() if CurrentChapter.is_empty)

	@property
	def id(self) -> int:
		"""Уникальный идентификатор ветви."""

		return self._ID

	#==========================================================================================#
	# >>>>> НАСЛЕДУЕМЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def _from_sequence(self, chapters: Sequence[BaseChapter]) -> dict[int, BaseChapter]:
		"""
		Преобразует последовательность глав в словарь.

		:param chapters: Последовательность глав.
		:type chapters: Sequence[BaseChapter]
		:return: Словарь глав.
		:rtype: dict[int, BaseChapter]
		"""

		return {CurrentChapter.id: CurrentChapter for CurrentChapter in chapters}

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, branch_id: int):
		"""
		Ветвь контента.

		:param branch_id: ID ветви.
		:type branch_id: int
		"""

		self._ID = branch_id
		self._Chapters: dict[int, BaseChapter] = {}

	def add_chapter(self, chapter: BaseChapter):
		"""
		Добавляет главу в ветвь. Если глава с таким ID уже существует, добавление не происходит.

		:param chapter: Данные главы.
		:type chapter: BaseChapter
		:raises ParsingError: Выбрасывается при отсутствии у добавляемой главы ID.
		"""

		if chapter.id is None:
			raise exceptions.parsing.ParsingError("Chapter must have unique ID.")
		
		if chapter.id in tuple(Value.id for Value in self._Chapters.values()):
			return
		
		self._Chapters[chapter.id] = chapter

	def get_chapter_by_id(self, chapter_id: int) -> BaseChapter:
		"""
		Возвращает главу по её уникальному идентификатору.

		:param chapter_id: ID главы.
		:type id: int
		:return: Глава.
		:rtype: BaseChapter
		:raises KeyError: Глава не найдена.
		"""

		return self._Chapters[chapter_id]
	
	def has_chapter(self, chapter_id: int) -> bool:
		"""
		Проверяет, содержится ли глава с таким ID в ветви.

		:param chapter_id: ID главы.
		:type id: int
		:return: Возвращает `True`, если глава с таким ID присутствует.
		:rtype: bool
		"""

		return chapter_id in self._Chapters
	
	def remove_chapter(self, chapter_id: int):
		"""
		Удаляет главу из ветви.

		:param chapter_id: ID главы.
		:type id: int
		:raises KeyError: Глава не найдена.
		"""
		
		del self._Chapters[chapter_id]

	def replace_chapter_by_id(self, chapter: BaseChapter, chapter_id: int):
		"""
		Заменяет главу в ветви по её ID.

		:param chapter: Новая глава.
		:type chapter: BaseChapter
		:param id: ID заменяемой главы.
		:type id: int
		:raises KeyError: Глава не найдена.
		"""

		self.get_chapter_by_id(chapter_id)
		self._Chapters[chapter_id] = chapter
	
	def reverse(self):
		"""Инвертирует порядок глав в ветви."""

		self._Chapters = self._from_sequence(tuple(reversed(self._Chapters.values())))

	def sort(self):
		"""
		По умолчанию помещает главы в порядке возрастания их нумерации.

		Переопределите данный метод для использования иных алгоритмов сортировки.
		"""

		self._Chapters = self._from_sequence(sorted(
			self._Chapters.values(),
			key = lambda Value: (
				list(map(int, Value.volume.split(".") if Value.volume else "")),
				list(map(int, Value.number.split(".") if Value.number else ""))
			)
		))

	def to_list(self) -> list[dict]:
		"""Возвращает список словарей данных глав, принадлежащих текущей ветви."""

		return [chapter.to_dict() for chapter in self._Chapters.values()]
	