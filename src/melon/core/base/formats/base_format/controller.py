import hashlib
import os
import shutil
from abc import ABC, abstractmethod
from json import JSONDecodeError
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

import orjson

from dublib.functions.data import zerotify
from dublib.functions.filesystem import json

from .... import exceptions
from .enums import By, ImagesTypes
from .structs import SavingResult

if TYPE_CHECKING:
	from ...parsers.base_parser import BaseParser
	from ...parsers.components.settings import CustomSettingsTemplate
	from ...source_operator import BaseSourceOperator
	from .data import BaseTitleData

class BaseTitleController[TD: "BaseTitleData"](ABC):
	"""Базовый контроллер тайтла."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def chapters_count(self) -> int:
		"""Количество глав во всех ветвях."""

		return sum(Branch.chapters_count for Branch in self._data.branches)

	@property
	def data(self) -> TD:
		"""Данные тайтла."""

		return self._data

	@property
	def empty_chapters_count(self) -> int:
		"""Количество глав без контента во всех ветвях."""

		return sum(Branch.empty_chapters_count for Branch in self._data.branches)

	@property
	def images_directory(self) -> Path:
		"""Путь к директории изображений тайтла."""

		directory = self._parser.settings.directories.images / self.used_filename
		directory.mkdir(exist_ok = True)

		return directory

	@property
	def is_local_file_loaded(self) -> bool:
		"""Состояние: считывались ли данные из локального файла."""

		return bool(self._local_file_path)

	@property
	def parser(self) -> "BaseParser":
		"""Парсер."""

		return self._parser

	@property
	def path(self) -> Path:
		"""Путь к файлу."""

		return self._parser.settings.directories.titles / f"{self.used_filename}.json"

	@property
	def used_filename(self) -> str:
		"""Используемое имя файла."""

		if self._parser.settings.common.use_id_as_filename and self._data.id is not None:
			return str(self._data.id)

		return self._slug

	#==========================================================================================#
	# >>>>> НАСЛЕДУЕМЫЕ МЕТОДЫ ЧТЕНИЯ ЛОКАЛЬНЫХ ФАЙЛОВ <<<<< #
	#==========================================================================================#
	
	def _load_data_by_filename(self, filename: str) -> dict | None:

		Filename: str = filename if filename.endswith(".json") else f"{filename}.json"
		FilePath = self._parser.settings.directories.titles / Filename

		if FilePath.exists():
			self._local_file_path = FilePath
			return json.read(FilePath)

		return None

	def _load_data_by_id(self, title_id: int) -> dict | None:

		Journal = self._parser.source_operator.shared_data.journal
		TitlesDirectory = self._parser.settings.directories.titles
	
		if not self._parser.settings.common.use_id_as_filename:
			Slug = Journal.get_slug_by_id(title_id)

			if Slug:
				FilePath = TitlesDirectory / f"{Slug}.json"
				if FilePath.exists(): return json.read(FilePath)

		else:
			FilePath = TitlesDirectory / f"{title_id}.json"
			if FilePath.exists(): return json.read(FilePath)

		return self._search_file_in_directory(TitlesDirectory, title_id, By.ID) or {}

	def _load_data_by_slug(self, slug: str) -> dict | None:

		Journal = self._parser.source_operator.shared_data.journal
		TitlesDirectory = self._parser.settings.directories.titles

		if self._parser.settings.common.use_id_as_filename:
			ID = Journal.get_id_by_slug(slug)

			if ID:
				FilePath = TitlesDirectory / f"{ID}.json"
				if FilePath.exists(): return json.read(FilePath)

		else:
			FilePath = TitlesDirectory / f"{slug}.json"
			if FilePath.exists(): return json.read(FilePath)
		
		return self._search_file_in_directory(TitlesDirectory, slug, By.Slug)

	def _load_data(self, identificator: int | str, selector_type: By = By.Slug) -> dict | None:
		"""
		Открывает локальный JSON файл и считывает его данные.

		:param identificator: Идентификатор тайтла: имя файла (без расширения), ID или алиас тайтла.
		:type identificator: int | str
		:param selector_type: Режим поиска файла. По умолчанию `By.Slug` – идентификатор соответствует алиасу тайтла.
		:type selector_type: By
		:return: Словарь данных тайтла или `None` при отсутствии файла.
		:rtype: dict | None
		:raises JSONDecodeError: Ошибка десериализации JSON.
		:raises UnsupportedFormat: Неподдерживаемый формат JSON.
		"""

		DataBuffer: dict | None = None

		match selector_type:

			case By.Filename:
				if type(identificator) is not str: raise ValueError("Filename must be str.")
				DataBuffer = self._load_data_by_filename(identificator)
				
			case By.Slug:
				if type(identificator) is not str: raise ValueError("Slug must be str.")
				DataBuffer = self._load_data_by_slug(identificator)

			case By.ID:
				if type(identificator) is not int: raise ValueError("ID must be int.")
				DataBuffer = self._load_data_by_id(identificator)

		self._IsLocalFileLoaded = bool(DataBuffer)

		return zerotify(DataBuffer)

	def _search_file_in_directory(self, directory: str | PathLike[str], identificator: int | str, identificator_type: Literal[By.ID, By.Slug]) -> dict | None:
		"""
		Находит файл JSON в директории по идентификатору определённого типа.

		:param directory: Путь к каталогу файлов.
		:type directory: str | PathLike[str]
		:param identificator: Идентификатор: ID или алиас.
		:type identificator: int | str
		:param identificator_type: Тип идентификатора.
		:type identificator_type: Literal[By.ID, By.Slug]
		:return: Содержимое файла или `None` при отсутствии оного или ошибке.
		:rtype: dict | None
		"""

		for Element in os.scandir(directory):
			if not Element.is_file() or not Element.name.endswith(".json"): continue

			try: 
				Data = json.read(Element.path)
				if Data.get(identificator_type.value) == identificator:
					self._local_file_path = Path(Element.path)
					return Data

			except (JSONDecodeError, exceptions.parsers.UnsupportedFormat): pass

		return None

	#==========================================================================================#
	# >>>>> НАСЛЕДУЕМЫЕ МЕТОДЫ ОЧИСТКИ ИЗОБРАЖЕНИЙ <<<<< #
	#==========================================================================================#

	def _clear_unused_images(self) -> int:
		"""
		Удаляет неиспользуемые файлы изображений в стандартных каталогах и пустые папки.

		:return: Количество удалённых файлов.
		:rtype: int
		"""

		unused_files_removed: int = self._clear_unused_covers_images()
		unused_files_removed += self._clear_unused_persons_images()
		self._remove_empty_images_directories()

		return unused_files_removed

	def _clear_unused_covers_images(self) -> int:
		"""
		Удаляет неиспользуемые изображения обложек.

		:return: Количество удалённых файлов.
		:rtype: int
		"""

		covers_directory = self.images_directory / "covers"

		if not covers_directory.exists():
			return 0

		used_files: tuple[str, ...] = tuple(cover.filename for cover in self.data.covers)
		unused_files_count: int = 0

		for file in os.listdir(covers_directory):
			if file not in used_files:
				unused_files_count += 1
				unused_file = covers_directory / file
				unused_file.unlink(missing_ok = True)

		return unused_files_count

	def _clear_unused_persons_images(self) -> int:
		"""
		Удаляет неиспользуемые изображения персонажей.

		:return: Количество удалённых файлов.
		:rtype: int
		"""

		persons_directory = self.images_directory / "persons"

		if not persons_directory.exists():
			return 0

		used_files: list[str] = []
		unused_files_count: int = 0

		for person in self.data.perons:
			for image in person.images:
				used_files.append(image.filename)

		for file in os.listdir(persons_directory):
			if file not in used_files:
				unused_files_count += 1
				unused_file = persons_directory / file
				unused_file.unlink(missing_ok = True)

		return unused_files_count

	def _remove_empty_images_directories(self):
		"""Удаляет пустые каталоги в директории изображений тайтла и саму директорию, если пуста."""

		images_directory = self.images_directory

		for entry_point in os.scandir(images_directory):
			if not entry_point.is_dir(): continue
			directory = Path(entry_point.path)

			if not any(directory.iterdir()):
				directory.rmdir()

		if not any(images_directory.iterdir()):
			images_directory.rmdir()

	#==========================================================================================#
	# >>>>> НАСЛЕДУЕМЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def _is_local_file_equal(self, data: dict) -> bool:
		"""
		Проверяет, идентичны ли данные тайтла локальным данным.

		:param data: Словарное представление данных тайтла.
		:type data: dict
		:return: Возвращает `True`, если данные идентичны, или `False` в противном случа и при отсутствии локального файла.
		:rtype: bool
		"""

		if not self.path.exists():
			return False

		try:
			local_hash = hashlib.sha256(orjson.dumps(json.read(self.path)))
			memore_hash = hashlib.sha256(orjson.dumps(data))
			
		except orjson.JSONDecodeError:
			return False
		
		return local_hash.hexdigest() == memore_hash.hexdigest()

	def _update_journal(self):
		"""Обновляет кэш пары алиас-ID."""

		if self._data.id:
			self._parser.source_operator.shared_data.journal.update(self._data.id, self._data.slug)

	#==========================================================================================#
	# >>>>> ПЕРЕОПРЕДЕЛЯЕМЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#
	
	@abstractmethod
	def _export_data_type(self) -> type[TD]:
		"""
		Экспортирует тип данных тайтла.

		:return: Тип данных тайтла.
		:rtype: type[BaseTitleData]
		"""

		pass

	def _post_init(self):
		"""Метод, выполняющийся после инициализации объекта."""

		pass

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, parser: "BaseParser", slug: str):

		self._parser: "BaseParser[BaseSourceOperator, CustomSettingsTemplate]" = parser
		self._slug: str = slug

		self._data: TD = self._export_data_type()(
			title_controller = self,
			title_format = "melon-" + type(self).__name__.lower()
		)
		self._data.set_domain(self._parser.manifest.domain)
		self._data.set_slug(self._slug)

		self._local_file_path: Path | None = None

		self._post_init()

	def get_images_type_directory(self, images_type: ImagesTypes, create: bool = True) -> Path:
		"""
		Возвращает путь к директории типа изображений, автоматически создаёт её.

		:param images_type: Тип изображений.
		:type images_type: ImagesTypes
		:param create: Указывает, пытаться ли создавать директорию.
		:type create: bool
		:return: Путь к существующей директории типа изображений.
		:rtype: Path
		"""

		directory = self.images_directory / images_type.value
		if create: directory.mkdir(exist_ok = True)

		return directory

	def load(self, identificator: int | str, selector_type: By = By.Slug) -> bool:
		"""
		Открывает локальный JSON файл и интерпретирует его данные.

		:param identificator: Идентификатор тайтла: имя файла (без расширения), ID или алиас тайтла.
		:type identificator: int | str
		:param selector_type: Режим поиска файла. По умолчанию `By.Slug` – идентификатор соответствует алиасу тайтла.
		:type selector_type: By
		:return: Возвращает `True`, если удалось найти и открыть файл.
		:rtype: bool
		"""

		data: dict | None = self._load_data(identificator, selector_type)
		if data: self._data.from_dict(data)

		return bool(data)

	def merge(self) -> int:
		"""
		Считывает данные о контенте тайтла.

		:return: Количество глав, для которых считан контент.
		:rtype: int
		"""

		DataBuffer: dict | None = self._load_data(self._slug)

		if not DataBuffer:
			return 0
		
		#---> Слияние размеров обложек.
		#==========================================================================================#
		CoversData: list[dict] = DataBuffer["covers"]

		for CoverData in CoversData:
			Link = CoverData["link"]
			TargetCover = self._data.find_cover(Link)

			if TargetCover:
				TargetCover.create_resolution(CoverData.get("width"), CoverData.get("height"))

		#---> Слияние размеров портретов персонажей.
		#==========================================================================================#
		PersonsData: list[dict] | None = DataBuffer.get("persons")

		if PersonsData:
			for PersonData in PersonsData:
				PersonObject = self._data.find_person(PersonData["name"])
				if not PersonObject: continue

				for CurrentImage in cast("list[dict]", PersonData["images"]):
					Link = CurrentImage["link"]
					TargetImage = PersonObject.find_image(Link)
					
					if TargetImage:
						TargetImage.create_resolution(CurrentImage.get("width"), CurrentImage.get("height"))
			
		#---> Слияние контента глав.
		#==========================================================================================#
		ContentData: dict[str, dict] = DataBuffer["content"]
		MergedChaptersCount: int = 0

		for BranchKey in ContentData.keys():
			for ChapterData in ContentData[BranchKey]:
				ChapterID = int(ChapterData["id"])
				
				SearchResult = self._data.find_chapter(ChapterID)

				if SearchResult and SearchResult.chapter.is_empty:
					SearchResult.chapter.from_dict(ChapterData)
					MergedChaptersCount += 1

		return MergedChaptersCount

	def remove_images_type_directory(self, images_type: ImagesTypes):
		"""
		Удаляет директорию типа изображений со всем содержимым.

		:param images_type: Тип изображений.
		:type images_type: ImagesTypes
		"""

		directory = self.get_images_type_directory(images_type, create = False)

		if directory.exists():
			shutil.rmtree(directory)

	def save(self, sorting: bool = False) -> SavingResult:
		"""
		Сохраняет данные тайтла в локальный файл JSON.

		:param sorting: Указывает, нужно ли провести сортировку глав на основе их нумерации.
		:type sorting: bool
		:return: Результат сохранения тайтла.
		:rtype: SavingResult
		"""

		data: dict[str, Any] = self._data.to_dict(sorting)

		is_local_file_equal: bool = self._is_local_file_equal(data)
		is_slug_changed: bool = False
		is_local_file_renamed: bool = False

		if self._data.slug != self._slug:
			is_slug_changed = True

		if not is_local_file_equal:
			json.write(self.path, data)

		if not self._parser.settings.common.use_id_as_filename and is_slug_changed:
			original_path = self.path
			new_path = original_path.with_stem(self._data.slug)
			original_path.rename(new_path)
			self._slug = self._data.slug
			is_local_file_renamed = True

		self._update_journal()

		return SavingResult(
			is_saved = not is_local_file_equal,
			is_slug_changed = is_slug_changed,
			is_local_file_renamed = is_local_file_renamed,
			unused_images_removed = self._clear_unused_images()
		)
