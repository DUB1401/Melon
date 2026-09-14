from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Literal, Sequence, cast

from dublib.functions.data.dictionary import insert_item
from dublib.validators import types

from .... import exceptions
from ...parsers.components.words_dictionary import CheckLanguageCode
from ...structs.image import ImageData
from .branch import Branch
from .enums import Statuses
from .person import Person
from .structs import ChapterSearchResult, ExtraField

if TYPE_CHECKING:
	from .chapter import BaseChapter
	from .controller import BaseTitleController

class BaseTitleData[C: "BaseChapter"](ABC):
	"""Бозовые данные тайтла."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def format(self) -> Literal["melon-manga", "melon-ranobe"]:
		"""Формат данных."""

		return self._data["format"]

	@property
	def domain(self) -> str | None:
		"""Домен источника."""

		return self._data["domain"]

	@property
	def id(self) -> int | None:
		"""Целочисленный уникальный идентификатор тайтла."""

		return self._data["id"]

	@property
	def slug(self) -> str:
		"""Алиас."""

		return self._data["slug"]
	
	@property
	def content_language(self) -> str | None:
		"""Код языка контента по стандарту ISO 639-3."""

		return self._data["content_language"]

	@property
	def localized_name(self) -> str | None:
		"""Локализованное название."""

		return self._data["localized_name"]

	@property
	def eng_name(self) -> str | None:
		"""Название на английском."""

		return self._data["eng_name"]

	@property
	def another_names(self) -> tuple[str, ...]:
		"""Последовательность альтернативных названий."""

		return tuple(self._data["another_names"])
	
	@property
	def covers(self) -> tuple[ImageData, ...]:
		"""Последовательность данных обложек."""

		return tuple(self._covers)

	@property
	def authors(self) -> tuple[str, ...]:
		"""Последовательность авторов."""

		return tuple(self._data["authors"])

	@property
	def publication_year(self) -> int | None:
		"""Год публикации."""

		return self._data["publication_year"]

	@property
	def description(self) -> str | None:
		"""Описание."""

		return self._data["description"]

	@property
	def age_limit(self) -> int | None:
		"""Возрастное ограничение."""

		return self._data["age_limit"]

	@property
	def genres(self) -> tuple[str, ...]:
		"""Последовательность жанров."""

		return tuple(self._data["genres"])

	@property
	def tags(self) -> tuple[str, ...]:
		"""Последовательность тегов."""

		return tuple(self._data["tags"])

	@property
	def franchises(self) -> tuple[str, ...]:
		"""Последовательность франшиз."""

		return tuple(self._data["franchises"])
	
	@property
	def perons(self) -> tuple[Person, ...]:
		"""Последовательность персонажей."""

		return tuple(self._persons)
	
	@property
	def status(self) -> Statuses | None:
		"""Статус тайтла."""

		return self._data["status"]

	@property
	def is_licensed(self) -> bool | None:
		"""Состояние: лицензирован ли тайтл на данном ресурсе."""

		return self._data["is_licensed"]

	@property
	def branches(self) -> tuple[Branch, ...]:
		"""Последовательность ветвей тайтла."""

		return tuple(self._branches.values())
	
	#==========================================================================================#
	# >>>>> НАСЛЕДУЕМЫЕ МЕТОДЫ ПРЕОБРАЗОВАНИЯ КОНТЕЙНЕРОВ ДАННЫХ <<<<< #
	#==========================================================================================#

	def _parse_content(self):
		"""Парсит контент в объектные представления."""

		content: dict[str, list] = self._data["content"]

		for branch_id_string in content.keys():
			branch_data: list[dict] = content[branch_id_string]
			branch_id: int = int(branch_id_string)
			branch_buffer = Branch(branch_id)

			for chapter_data in branch_data:
				chapter_id: int = chapter_data["id"]
				chapter_buffer = self._chapter_type(self._title_controller.parser, chapter_id)
				chapter_buffer.from_dict(chapter_data)
				branch_buffer.add_chapter(chapter_buffer)

			self.add_branch(branch_buffer)

	def _parse_covers(self):
		"""Парсит обложки в объектные представления."""

		self._covers.clear()

		for CoverData in self._data["covers"]:
			CoverData = cast("dict", CoverData)
			Buffer = ImageData(CoverData["link"])
			Buffer.create_resolution(CoverData.get("width"), CoverData.get("height"))
			self._covers.append(Buffer)

	def _parse_persons(self):
		"""Парсит персонажей в объектные представления."""

		self._persons.clear()

		for PersonData in self._data["persons"]:
			CoverData = cast("dict", PersonData)
			Buffer = Person(CoverData["name"])
			
			AnotherNames = CoverData.get("another_names") or ()
			Images = CoverData.get("images") or ()
			Description = CoverData.get("description")

			for AnotherName in AnotherNames:
				Buffer.add_another_name(AnotherName)

			for CurrentImageData in Images:
				CurrentImageData = cast("dict", CurrentImageData)
				Image = ImageData(CurrentImageData["link"])
				Image.create_resolution(CurrentImageData.get("width"), CurrentImageData.get("height"))
				Buffer.add_image(Image)

			if Description:
				Buffer.set_description(Description)

			self._persons.append(Buffer)

	def _update_branches_info(self):
		"""Обновляет информацию о ветвях во внутреннем словарном хранилище тайтла."""

		Branches = []

		for CurrentBranch in self._branches.values():
			Branches.append({"id": CurrentBranch.id, "chapters_count": CurrentBranch.chapters_count})

		self._data["branches"] = sorted(Branches, key = lambda Value: Value["chapters_count"], reverse = True)

	def _build_conent(self, brach_id: int | None = None, sorting: bool = True):
		"""
		Обновляет контент во внутреннем словарном хранилище данных тайтла.

		:param brach_id: Если указать ID ветви, будет обновлена только одна ветвь.
		:type brach_id: int | None
		:param sorting: Указывает, нужно ли провести сортировку глав на основе их нумерации.
		:type sorting: bool
		"""

		for branch in self._branches.values():
			if brach_id and brach_id == branch.id or not brach_id:
				if sorting: branch.sort()
				self._data["content"][str(branch.id)] = branch.to_list()
				if brach_id: break

	def _build_covers(self):
		"""Обновляет данные обложек во внутреннем словарном хранилище данных тайтла."""

		self._data["covers"] = []

		for CurrentCover in self._covers:
			self._data["covers"].append(CurrentCover.to_dict())

	def _build_persons(self):
		"""Обновляет данные персонажей во внутреннем словарном хранилище данных тайтла."""

		self._data["persons"] = []

		for CurrentPerson in self._persons:
			self._data["persons"].append(CurrentPerson.to_dict(self._title_controller.parser.settings.common.sizing_images))

	#==========================================================================================#
	# >>>>> НАСЛЕДУЕМЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def _generate_data_struct(self) -> dict[str, Any]:
		"""
		Генерирует базовое словарное представление тайтла.

		:return: Базовое словарное представление тайтла.
		:rtype: dict[str, Any]
		"""

		data: dict[str, Any] = {
			"format": None,
			"domain": None,
			"id": None,
			"slug": None,
			"content_language": None,

			"localized_name": None,
			"eng_name": None,
			"another_names": [],
			"covers": [],

			"authors": [],
			"publication_year": None,
			"description": None,
			"age_limit": None,
			"status": None,
			"is_licensed": None,
			
			"genres": [],
			"tags": [],
			"franchises": [],
			"persons": [],
			
			"branches": [],
			"content": {} 
		}

		for extra_field in self._export_extra_fields():
			data = insert_item(data, extra_field.after_key, (extra_field.name, extra_field.value))

		return data

	def _merge_branch(self, branch: Branch) -> int:
		"""
		Выполняет слияние переданной ветви с ветвью, имеющей такой же ID.

		:param branch: Ветвь.
		:type branch: Branch
		:return: Количество добавленных глав.
		:rtype: int
		"""

		CurrentBranch = self._branches[branch.id]
		AddedCount = 0

		for NewChapter in branch.chapters:
			if not CurrentBranch.has_chapter(NewChapter.id):
				CurrentBranch.add_chapter(NewChapter)
				AddedCount += 1

		return AddedCount

	def _remove_cover(self, link: str):
		"""
		Удаляет обложку по ссылке.

		:param link: Ссылка.
		:type link: str
		"""

		result = self.find_cover(link)

		if result:
			self._covers.remove(result)

	#==========================================================================================#
	# >>>>> ПЕРЕОПРЕДЕЛЯЕМЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	@abstractmethod
	def _export_chapter_type(self) -> type[C]:
		"""
		Экспортирует тип главы.

		:return: Тип главы.
		:rtype: type[BaseChapter]
		"""

		pass

	def _export_extra_fields(self) -> Sequence[ExtraField]:
		"""
		Экспортирует последовательность дополнительных корневых полей данных.

		:return: Последовательность дополнительных корневых полей данных.
		:rtype: Sequence[ExtraField]
		"""

		return ()

	def _post_init(self):
		"""Метод, выполняющийся после инициализации объекта."""

		pass

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, title_controller: "BaseTitleController[BaseTitleData]", title_format: str):
		"""
		Базовые данные тайтла.

		:param title_controller: Контроллер тайтла.
		:type title_controller: BaseTitleController
		:param title_format: Формат тайтла.
		:type title_format: str
		"""

		self._title_controller = title_controller

		self._data: dict[str, Any] = self._generate_data_struct()
		self._data["format"] = title_format
		self._chapter_type: type[C] = self._export_chapter_type()

		self._covers: list[ImageData] = []
		self._persons: list[Person] = []
		self._branches: dict[int, Branch] = {}
		
		self._post_init()

	def from_dict(self, data: dict):
		"""
		Заполняет данные тайтла из переданного словаря.

		:param data: Словарь данных.
		:type data: dict
		"""

		self._data = self._data | data

		self._parse_covers()
		self._parse_persons()
		self._parse_content()

	def to_dict(self, sorting: bool = True) -> dict[str, Any]:
		"""
		Возвращает словарное представление объекта.
		:param sorting: Указывает, нужно ли провести сортировку глав на основе их нумерации.
		:type sorting: bool

		:return: Словарное представление объекта.
		:rtype: dict[str, Any]
		"""

		self._build_covers()
		self._build_persons()
		self._update_branches_info()
		self._build_conent(sorting = sorting)
		
		return self._data.copy()

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ ПОИСКА ДАННЫХ <<<<< #
	#==========================================================================================#

	def find_branch(self, branch_id: int) -> Branch | None:
		"""
		Ищет ветвь по её ID.

		:param branch_id: ID dtndb.
		:type branch_id: int
		:return: Результат поиска.
		:rtype: Branch | None
		"""

		return self._branches.get(branch_id)

	def find_cover(self, link: str) -> ImageData | None:
		"""
		Производит поиск обложки по ссылке.

		:param link: Ссылка на обложку.
		:type link: str
		:return: Обложка или `None` при отсутствии оной.
		:rtype: ImageData | None
		"""

		for CurrentCover in self._covers:
			if CurrentCover.link == link:
				return CurrentCover
			
		return None

	def find_chapter(self, chapter_id: int) -> ChapterSearchResult | None:
		"""
		Ищет главу по её ID.

		:param chapter_id: ID главы.
		:type chapter_id: int
		:return: Результат поиска.
		:rtype: ChapterSearchResult | None
		"""

		BranchResult = None
		ChapterResult = None

		for CurrentBranch in self._branches.values():
			for CurrentChapter in CurrentBranch.chapters:
				if CurrentChapter.id == chapter_id:
					BranchResult = CurrentBranch
					ChapterResult = CurrentChapter
					break

		if all((BranchResult, ChapterResult)):
			return ChapterSearchResult(cast("Branch", BranchResult), ChapterResult) if ChapterResult else None

		return None

	def find_person(self, name: str) -> Person | None:
		"""
		Производит поиск персонажа по имени.

		:param name: Имя персонажа.
		:type name: str
		:return: Обложка или `None` при отсутствии оной.
		:rtype: ImageData | None
		"""

		for CurrentPerson in self._persons:
			if CurrentPerson.name == name:
				return CurrentPerson
			
		return None

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ УДАЛЕНИЯ ДАННЫХ <<<<< #
	#==========================================================================================#

	def clear_covers(self):
		"""Удаляет данные обо всех обложках."""

		self._covers.clear()

	def remove_cover(self, link: str) -> bool:
		"""
		Удаляет обложку.

		:param link: Ссылка на обложку.
		:type link: str
		:return: Возвращает `True`, если обложка найдена и удалена.
		:rtype: bool
		"""

		cover = self.find_cover(link)

		if cover:
			self._covers.remove(cover)
			return True

		return False

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ ДОБАВЛЕНИЯ ДАННЫХ В КОНТЕЙНЕРЫ <<<<< #
	#==========================================================================================#

	def add_another_name(self, another_name: str):
		"""
		Добавляет альтернативное название.

		:param another_name: Название.
		:type another_name: str
		"""
		
		another_name = another_name.strip()
		if another_name != self._data["localized_name"] and another_name != self._data["eng_name"] and another_name and another_name not in self._data["another_names"]:
			self._data["another_names"].append(another_name)

	def add_cover(self, cover: ImageData):
		"""
		Добавляет обложку.

		:param cover: Обложка.
		:type cover: ImageData
		:raises ValueError: Отсутствует ссылка на обложку.
		"""

		if not cover.link:
			raise ValueError("Cover must have a link.")
		
		for CurrentCover in self._covers:
			if CurrentCover.link == cover.link:
				return
		
		self._covers.append(cover)

	def add_author(self, author: str):
		"""
		Добавляет автора.

		:param author: Имя автора.
		:type author: str
		"""

		author = author.strip()
		if author and author not in self._data["authors"]:
			self._data["authors"].append(author)

	def add_genre(self, genre: str):
		"""
		Добавляет жанр.

		:param genre: Жанр.
		:type genre: str
		"""

		genre = genre.strip()
		if genre not in self._data["genres"]:
			self._data["genres"].append(genre)

	def add_tag(self, tag: str):
		"""
		Добавляет тег.

		:param tag: Тег.
		:type tag: str
		"""

		tag = tag.strip()
		if tag not in self._data["tags"]:
			self._data["tags"].append(tag)

	def add_franchise(self, franchise: str):
		"""
		Добавляет франшизу.

		:param franchise: Франшиза.
		:type franchise: str
		"""

		franchise = franchise.strip()
		if franchise and franchise not in self._data["franchises"]:
			self._data["franchises"].append(franchise)

	def add_person(self, person: Person):
		"""
		Добавляет персонажа.

		:param person: Персонаж.
		:type person: Person
		"""
		
		for CurrentPerson in self._persons:
			if CurrentPerson.name == person.name:
				return
			
		self._persons.append(person)

	def add_branch(self, branch: Branch) -> int:
		"""
		Добавляет ветвь.

		:param branch: Ветвь контента. Если ветвь с таким ID уже существует, будут добавлены только отсутствующие главы.
		:type branch: Branch
		:return: Количество добавленных глав.
		:rtype: int
		:raises ParsingError: Ветвь не имеет ID или ветвь с таким ID уже добавлена в тайтл.
		"""

		AddedCount = branch.chapters_count

		if not branch.id:
			exceptions.parsing.ParsingError("Branch must have ID.")

		if branch.id in self._branches.keys():
			AddedCount = self._merge_branch(branch)
		else:
			self._branches[branch.id] = branch
			self._branches = {CurrentBranch.id: CurrentBranch for CurrentBranch in sorted(self._branches.values(), key = lambda Value: Value.chapters_count, reverse = True)}

		return AddedCount

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ УСТАНОВКИ КОНТЕЙНЕРОВ <<<<< #
	#==========================================================================================#

	def set_another_names(self, another_names: Sequence[str]):
		"""
		Задаёт набор альтернативных названий.

		:param another_names: Набор альтернативных названий.
		:type another_names: Sequence[str]
		"""

		for Name in another_names:
			self.add_another_name(Name)

	def set_covers(self, covers: Sequence[ImageData]):
		"""
		Задаёт последовательность обложек.

		:param covers: Последовательность обложек.
		:type covers: Sequence[Cover]
		:raises ValueError: Выбрасывается при отсутствии ссылки в данных обложки.
		"""

		for CurrentCover in covers:
			self.add_cover(CurrentCover)

	def set_authors(self, authors: Sequence[str]):
		"""
		Задаёт список авторов.

		:param authors: Список авторов.
		:type authors: Sequence[str]
		"""

		for Author in authors:
			self.add_author(Author)

	def set_genres(self, genres: Sequence[str]):
		"""
		Задаёт список жанров.

		:param genres: Список жанров.
		:type genres: Sequence[str]
		"""

		for Genre in genres:
			self.add_genre(Genre)

	def set_tags(self, tags: Sequence[str]):
		"""
		Задаёт список тегов.

		:param tags: Список тегов.
		:type tags: Sequence[str]
		"""

		for Tag in tags:
			self.add_tag(Tag)

	def set_franchises(self, franchises: Sequence[str]):
		"""
		Задаёт список франшиз.

		:param franchises: Список франшиз.
		:type franchises: Sequence[str]
		"""

		for Franchise in franchises:
			self.add_franchise(Franchise)

	def set_persons(self, persons: Sequence[Person]):
		"""
		Задаёт список персонажей.

		:param persons: Список персонажей.
		:type persons: Sequence[Person]
		"""
		
		for CurrentPerson in persons:
			self.add_person(CurrentPerson)

	# To-Do: реализовать set_branches().

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ УСТАНОВКИ СВОЙСТВ <<<<< #
	#==========================================================================================#

	def set_domain(self, domain: str | None):
		"""
		Задаёт домен источника.

		:param site: Домен источника.
		:type site: str | None
		:raises ValueError: Некорректный домен.
		"""

		if domain and not types.Domain.validate(domain):
			raise ValueError("Incorrect domain.")

		self._data["domain"] = domain

	def set_id(self, title_id: int | None):
		"""
		Задаёт ID тайтла.

		:param id: ID тайтла.
		:type id: int | None
		"""

		self._data["id"] = title_id

	def set_content_language(self, language_code: str | None, load_preset: bool = True):
		"""
		Задаёт язык контента по стандарту ISO 639-3.

		:param original_language: Код языка.
		:type original_language: str | None
		:param load_preset: Указывает, стоит ли попытаться загрузить готовый словарь ключевых локальных определений.
		:type load_preset: bool
		:raise ValueError: Выбрасывается при несоответствии кода языка стандарту.
		"""

		if language_code:
			CheckLanguageCode(language_code)

			if load_preset:
				self._title_controller.parser.load_words_dictionary_preset(language_code)

		self._data["content_language"] = language_code

	def set_localized_name(self, localized_name: str | None):
		"""
		Задаёт локализованное название тайтла.

		:param localized_name: Локализованное название.
		:type localized_name: str | None
		"""

		self._data["localized_name"] = localized_name.strip() if localized_name else None

	def set_eng_name(self, eng_name: str | None):
		"""
		Задаёт название на английском языке.

		:param eng_name: Название на английском языке.
		:type eng_name: str | None
		"""

		self._data["eng_name"] = eng_name.strip() if eng_name else None

	def set_publication_year(self, publication_year: int | None):
		"""
		Задаёт год публикации тайтла.

		:param publication_year: Год публикации тайтла.
		:type publication_year: int | None
		"""

		self._data["publication_year"] = publication_year

	def set_description(self, description: str | None):
		"""
		Задаёт описание тайтла.

		:param description: Описание тайтла.
		:type description: str | None
		"""

		self._data["description"] = description.strip() if description else None

	def set_age_limit(self, age_limit: int | None):
		"""
		Задаёт возрастной рейтинг.

		:param age_limit: Возрастной рейтинг.
		:type age_limit: int | None
		"""

		self._data["age_limit"] = age_limit

	def set_slug(self, slug: str):
		"""
		Изменяет алиас тайтла. Если алиас используется в качестве имени описательного файла, последний будет переименован соответственно.

		:param slug: Алиас тайтла.
		:type slug: str
		"""

		if slug == self.slug:
			return

		self._data["slug"] = slug

	def set_status(self, status: Statuses | None):
		"""
		Задаёт статус тайтла.

		:param status: Статус тайтла.
		:type status: Statuses | None
		"""

		self._data["status"] = status.value if status else None
	
	def set_is_licensed(self, is_licensed: bool | None):
		"""
		Задаёт состояние: лицензирован ли тайтл в источнике.

		:param is_licensed: Состояние: лицензирован ли тайтл в источнике.
		:type is_licensed: bool | None
		"""

		self._data["is_licensed"] = is_licensed