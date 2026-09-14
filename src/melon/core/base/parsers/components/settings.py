import re
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal

from deepmerge import always_merger
from pydantic import TypeAdapter
from pydantic.dataclasses import dataclass

from dublib.functions.data import zerotify
from dublib.functions.filesystem import json
from dublib.web_requestor import Proxy

from ...extensions.options import BaseExtensionOptions

if TYPE_CHECKING:
	from .....core.system_objects import SystemObjects
	from ...structs.image import ImageResolution

#==========================================================================================#
# >>>>> СТАНДАРТНЫЕ НАСТРОЙКИ <<<<< #
#==========================================================================================#

_BASE_SETTINGS = MappingProxyType({
	"directories": {
		"content": None,
		"images": None,
		"titles": None
	},
	"common": {
		"pretty": True,
		"use_id_as_filename": False,
		"sizing_images": True
	},
	"network": {
		"delay": 1.0,
		"retries": 1,
		"proxies": [],
		"images_mirrors": {}
	},
	"filters": {
		"text": {
			"regexs": [],
			"strings": []
		},
		"images": {
			"min_height": None,
			"min_width": None,
			"max_height": None,
			"max_width": None,
			"min_size": 100,
			"signatures": []
		}
	},
	"custom": {},
	"extensions": {}
})

#==========================================================================================#
# >>>>> ВНУТРЕННИЕ СТРУКТУРЫ ДАННЫХ КАТЕГОРИЙ <<<<< #
#==========================================================================================#

@dataclass(frozen = True)
class CustomSettingsTemplate:
	"""Шаблон модели собственных настроек парсера."""

	pass

class TextFilters:
	"""Фильтры текста."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def regexs(self) -> list[str]:
		"""Список регулярных выражений фильтрации."""

		return self.__Data.get("regexs", [])
	
	@property
	def strings(self) -> list[str]:
		"""Список удаляемых строк."""

		return self.__Data.get("strings", [])

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, data: dict):
		"""
		Фильтры текста.

		:param data: Словарь фильтров текста.
		:type data: dict
		"""

		self.__Data: dict = data

	def clear(self, text: str) -> str:
		"""
		Очищает текст согласно фильтрам.

		:param text: Обрабатываемый текст.
		:type text: str
		:return: Обработанный текст.
		:rtype: str
		"""

		for Regex in self.regexs: text = re.sub(Regex, "", text)
		for String in self.strings: text = text.replace(String, "")

		return text

class ImagesFilters:
	"""Фильтры изображений."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def min_height(self) -> int | None:
		"""Минимальная высота изображения."""

		return self.__data["min_height"]
	
	@property
	def min_size(self) -> int:
		"""Минимальный размер изображения в байтах."""

		return self.__data["min_size"] or 0

	@property
	def min_width(self) -> int | None:
		"""Минимальная ширина изображения."""

		return self.__data["min_width"]
	
	@property
	def max_height(self) -> int | None:
		"""Максимальная высота изображения."""

		return self.__data["max_height"]
	
	@property
	def max_width(self) -> int | None:
		"""Максимальная ширина изображения."""

		return self.__data["max_width"]
	
	@property
	def signatures(self) -> tuple[str, ...]:
		"""Последовательность сигнатур изображений."""

		return tuple(self.__data["signatures"])

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, data: dict):
		"""
		Фильтры изображений.

		:param data: Словарь фильтров изображений.
		:type data: dict
		"""

		self.__data: dict = data

	def check_resolution(self, resolution: "ImageResolution") -> bool:
		"""
		Проверяет, выходит ли размер изображения за пределы разрешённых значений.

		:param resolution: Разрешение изображения в пикселях.
		:type resolution: ImageResolution
		:return: Возвращает `True` при корректном разрешении изображения..
		:rtype: bool
		"""

		if self.min_width and resolution.width < self.min_width: return False
		if self.min_height and resolution.height < self.min_height: return False
		if self.max_width and resolution.height > self.max_width: return False
		if self.max_height and resolution.height > self.max_height: return False

		return True

#==========================================================================================#
# >>>>> КАТЕГОРИИ НАСТРОЕК <<<<< #
#==========================================================================================#

class Directories:
	"""Директории."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def content(self) -> Path:
		"""Путь к директории контента."""

		return self.__GetDirectory("content")
	
	@property
	def images(self) -> Path:
		"""Путь к директории изображений."""

		return self.__GetDirectory("images")
	
	@property
	def titles(self) -> Path:
		"""Путь к директории файлов тайтлов."""

		return self.__GetDirectory("titles")
	
	#==========================================================================================#
	# >>>>> МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __GetDirectory(self, dir_type: Literal["content", "images", "titles"]) -> Path:
		"""
		Возвращает путь к каталогу. Автоматически создаёт его при отсутствии.

		:param dir_type: Тип каталога.
		:type dir_type: Literal["content", "images", "titles"]
		:return: Путь к каталогу.
		:rtype: Path
		"""

		Directory: str | None = zerotify(self.__DirectoriesDict.get(dir_type))
		
		DirectoryPath: Path = Path(Directory) if Directory else Path(f"{self.__SystemObjects.options.DEFAULT_OUTPUT_DIR}/{self.__ParserName}/{dir_type}")
		if Directory in (None, "output"): DirectoryPath.mkdir(parents = True, exist_ok = True)

		return DirectoryPath

	def __init__(self, system_objects: "SystemObjects", parser_name: str, settings: dict[str, str | None]):
		"""
		Директории.

		:param system_objects: Коллекция системных объектов.
		:type system_objects: SystemObjects
		:param parser_name: Имя парсера.
		:type parser_name: str
		:param settings: Словарь настроек парсера.
		:type settings: dict[str, Any]
		"""

		self.__SystemObjects: "SystemObjects" = system_objects
		self.__ParserName: str = parser_name
		self.__DirectoriesDict: dict[str, str | None] = settings or {}

class Common:
	"""Базовые настройки."""

	@property
	def pretty(self) -> bool:
		"""Состояние: включено ли улучшение качества контента."""

		return self.__CommonSettings["pretty"]
	
	@property
	def sizing_images(self) -> bool:
		"""Указывает, нужно ли пытаться определить размер изображений."""

		return self.__CommonSettings["sizing_images"]

	@property
	def use_id_as_filename(self) -> bool:
		"""Указывает, нужно ли использовать ID в качестве имени описательного файла."""

		return self.__CommonSettings["use_id_as_filename"]

	def __init__(self, settings: dict[str, Any]):
		"""
		Базовые настройки.

		:param settings: Словарь базовых настроек.
		:type settings: dict
		"""

		self.__CommonSettings: dict[str, Any] = settings

class Network:
	"""Настройки сетевых подключений."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def delay(self) -> float:
		"""Интервал ожидания между последовательными запросами."""

		return self.__NetworkSettings["delay"]
	
	@property
	def images_mirrors(self) -> dict[str, str]:
		"""Словарь заменяемых доменов, используемый при скачивании изображений."""

		return self.__NetworkSettings["images_mirrors"]

	@property
	def proxies(self) -> tuple[Proxy, ...]:
		"""Набор прокси."""

		return self.__Proxies

	@property
	def retries(self) -> int:
		"""Количество повторов запроса при неудачном выполнении."""

		return self.__NetworkSettings["retries"]

	#==========================================================================================#
	# >>>>> ПРИВАТНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __ParseProxies(self) -> tuple[Proxy, ...]:
		"""
		Парсит строковые представления прокси.

		:return: Набор объектов данных прокси.
		:rtype: tuple[Proxy, ...]
		"""

		Proxies = []

		for String in self.__NetworkSettings["proxies"]:
			Proxies.append(Proxy().parse(String))
			
		return tuple(Proxies)

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, settings: dict[str, Any]):
		"""
		Настройки сетевых подключений.

		:param settings: Словарь базовых настроек.
		:type settings: dict
		"""

		self.__NetworkSettings: dict[str, Any] = settings

		self.__Proxies: tuple[Proxy, ...] = self.__ParseProxies()

class Filters:
	"""Фильтры контента."""

	@property
	def text(self) -> TextFilters:
		"""Фильтры текста."""

		return self.__TextFilters
	
	@property
	def images(self) -> ImagesFilters:
		"""Фильтры изображений."""

		return self.__ImagesFilters

	def __init__(self, settings: dict):
		"""
		Фильтры контента.

		:param settings: Словарь фильтров.
		:type settings: dict
		"""

		self.__TextFilters = TextFilters(settings.get("text", {}))
		self.__ImagesFilters = ImagesFilters(settings.get("images", {}))

class Custom:
	"""Собственные настройки парсера."""

	def __init__(self, settings: dict[str, Any]):
		"""
		Собственные настройки парсера.

		:param settings: Словарь собственных настроек парсера.
		:type settings: dict[str, Any]
		"""

		self.__CustomSettings: dict = settings

	def __getitem__(self, key: str) -> Any:
		"""
		Возвращает значение настройки.

		:param key: Ключ настройки.
		:type key: str
		:return: Значение настройки.
		:rtype: Any
		:raises KeyError: Настройка не найдена.
		"""

		return self.__CustomSettings[key]

	def get(self, key: str, exception: bool = False) -> Any:
		"""
		Возвращает значение настройки.

		:param key: Ключ настройки.
		:type key: str
		:param exception: Указывает, нужно ли выбрасывать исключение типа `KeyError`.
		:type exception: bool
		:return: Значение настройки.
		:rtype: Any
		:raises KeyError: Настройка не найдена.
		"""

		if exception: 
			return self.__CustomSettings[key]

		return self.__CustomSettings.get(key)

class Extensions:
	"""Настройки расширений."""

	def __init__(self, settings: dict[str, Any]):
		"""
		Настройки расширений.

		:param settings: Словарь настроек расширений.
		:type settings: dict[str, Any]
		"""

		self.__extensions_settings: dict[str, dict] = settings

	def get[T: BaseExtensionOptions](self, extension_name: str, container: type[T]) -> T:
		"""
		Возвращает упакованные в контейнер опции расширения.

		:param extension_name: Имя расширения.
		:type extension_name: str
		:param container: Тип-контейнер, принимающий `dict | None` и представляющий в дальнейшем интерфейсы доступа к опциям. Наследуется от `BaseExtensionOptions`.
		:type container: type
		:return: Контейнер с опциями расширения.
		:rtype: BaseExtensionOptions
		:raises pydantic_core._pydantic_core.ValidationError: Неверный набор параметров расширения.
		"""
		
		return TypeAdapter(container).validate_python(self.__extensions_settings[extension_name])

#==========================================================================================#
# >>>>> ОСНОВНОЙ КЛАСС <<<<< #
#==========================================================================================#

class ParserSettings[T: CustomSettingsTemplate]:
	"""Настройки парсера."""

	#==========================================================================================#
	# >>>>> КАТЕГОРИИ НАСТРОЕК <<<<< #
	#==========================================================================================#

	@property
	def common(self) -> Common:
		"""Базовые настройки."""

		return self.__common

	@property
	def custom(self) -> T:
		"""Собственные настройки парсера."""

		if self.__custom is None:
			raise ValueError("Custom settings required, but unparsed.")

		return self.__custom
	
	@property
	def directories(self) -> Directories:
		"""Пути к директориям."""

		return self.__directories

	@property
	def extensions(self) -> Extensions:
		"""Настройки расширений."""

		return self.__extensions

	@property
	def filters(self) -> Filters:
		"""Фильтры контента."""

		return self.__filters

	@property
	def network(self) -> Network:
		"""Настройки сетевых подключений."""

		return self.__network

	#==========================================================================================#
	# >>>>> ПРИВАТНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __read(self) -> dict:
		"""
		Считывает настройки парсера из JSON в порядке приоритета: сначала из каталога конфигураций, затем из домашнего каталога парсера.

		:return: Словарь настроек парсера. При отстутствии таковых возвращает стандартный набор.
		:rtype: dict
		"""

		Settings: dict = self.get_base_settings(self.__system_objects, self.__parser_name)
		ConfigsPaths: tuple[Path, Path] = (
			self.__system_objects.manager.parsers.root / f"{self.__parser_name}/settings.json",
			self.__system_objects.options.CONFIGS_DIR.value / f"{self.__parser_name}.json"
		)

		for ConfigPath in ConfigsPaths:
			if ConfigPath.exists():
				Buffer: dict = json.read(ConfigPath)
				Settings = always_merger.merge(Settings, Buffer)

		return Settings

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, system_objects: "SystemObjects", parser_name: str):
		"""
		Настройки парсера.

		:param system_objects: Коллекция системных объектов.
		:type system_objects: SystemObjects
		:param parser_name: Имя парсера.
		:type parser_name: str
		"""
		
		self.__system_objects: "SystemObjects" = system_objects
		self.__parser_name: str = parser_name
		self.__settings: dict = self.__read()

		self.__directories = Directories(self.__system_objects, self.__parser_name, self.__settings.get("directories", {}))
		self.__common: Common = Common(self.__settings.get("common", {}))
		self.__network: Network = Network(self.__settings.get("network", {}))
		self.__filters = Filters(self.__settings.get("filters", {}))
		self.__extensions: Extensions = Extensions(self.__settings.get("extensions", {}))

		self.__custom: T | None = None

	@staticmethod
	def get_base_settings(system_objects: "SystemObjects", parser_name: str) -> dict:
		"""
		Возвращает словарь базовых настроек. Автоматически создаёт для каждого расширения секцию.

		:param system_objects: Коллекция системных объектов.
		:type system_objects: SystemObjects
		:param parser_name: Имя парсера.
		:type parser_name: str
		:return: Словарь базовых настроек.
		:rtype: dict
		"""

		BaseSetings: dict = _BASE_SETTINGS.copy()
		Extensions: tuple[str, ...] = system_objects.manager.parsers.get_operator(parser_name).extensions_names

		for ExtensionName in Extensions:
			BaseSetings["extensions"][ExtensionName] = {}

		return BaseSetings

	def parse_custom_settings(self, model: type[T]):
		"""
		Парсит кастомные настройки и подставляет их в структуру параметров.

		:param model: Модель кастомных настроек, представленная замороженным классом данных [pydantic](https://github.com/pydantic/pydantic), унаследованным от `CustomSettingsTemplate`.
		:type model: type[T]
		"""

		self.__custom = model(**self.__settings.get("custom", {}))