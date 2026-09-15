import importlib
import os
import shutil
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from dublib.functions.data import dictionary
from dublib.functions.decorators import run_before_method
from dublib.functions.filesystem import json

from ....core import exceptions
from ...base.parsers.components.manifest import ParserManifest
from ...base.parsers.components.settings import ParserSettings

if TYPE_CHECKING:
	from ...base.source_operator import BaseSourceOperator
	from . import Manager

#==========================================================================================#
# >>>>> ПЕРЕЧИСЛЕНИЯ <<<<< #
#==========================================================================================#

class ExportResults(Enum):
	"""Результаты экспорта настроек."""

	Missing = 0
	Installed = 1
	AlreadyExists = 2
	Overwtitten = 3
	Merged = 4

class ExportStrategies(Enum):
	"""Стратегии экспорта настроек."""

	Skip = "-s"
	Overwrite = "-o"
	Merge = "-m"

#==========================================================================================#
# >>>>> ОПЕРАТОР ПАРСЕРА <<<<< #
#==========================================================================================#

class ParserOperator:
	"""Оператор парсера."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	@run_before_method("_RequireInstallation")
	def extensions_names(self) -> tuple[str, ...]:
		"""Последовательность имён расширений парсера."""

		extensions_directory: Path = self.__Parsers.root / f"{self.__Name}/extensions"

		if not extensions_directory.exists():
			return ()

		return tuple(sorted(entry.name for entry in os.scandir(extensions_directory) if entry.is_dir() and not entry.name.startswith("__")))

	@property
	def is_installed(self) -> bool:
		"""Состояние: установлен ли парсер."""

		return self.__Parsers.is_installed(self.__Name, exception = False)

	@property
	def name(self) -> str:
		"""Имя парсера."""

		return self.__Name

	@property
	def path(self) -> Path:
		"""Путь к директории парсера."""

		return self.__Parsers.root / self.__Name

	@property
	def repository(self) -> str | None:
		"""URL удалённого репозитория."""

		return self.__Parsers.manager.repositories.get(self.__Name)

	@property
	def requirements_path(self) -> Path:
		"""Путь к файлу зависимостей если."""

		return self.path / "requirements.txt"

	#==========================================================================================#
	# >>>>> НАСЛЕДУЕМЫЕ ВАЛИДАТОРЫ <<<<< #
	#==========================================================================================#

	def _RequireInstallation(self):
		"""
		Проверяет, установлен ли парсер. Служит для использования в декораторе `run_before_method()`.

		:raises ParserNotFound: Парсер не установлен.
		"""

		self.__Parsers.is_installed(self.__Name)

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, parsers: "Parsers", name: str):
		"""
		Менеджер парсеров.

		:param parsers: Менеджер парсеров.
		:type parsers: Parsers
		:param name: Имя парсера.
		:type name: str
		"""

		self.__Parsers = parsers
		self.__Name = name

	@run_before_method("_RequireInstallation")
	def export_settings(self, strategy: ExportStrategies = ExportStrategies.Skip) -> ExportResults:
		"""
		Экспортирует настройки парсера.

		:param strategy: Стратегия экспорта настроек при конфликте файлов.
		:type strategy: ExportStrategies
		:return: Результат экспорта настроек.
		:rtype: ExportResults
		"""

		BaseConfig: dict = ParserSettings.get_base_settings(self.__Parsers.manager.system_objects, self.__Name)
		PresetFile = self.path / "settings.json"
		StorageFile = self.__Parsers.manager.system_objects.options.CONFIGS_DIR.value / f"{self.__Name}.json"

		if PresetFile.exists():
			Buffer: dict = json.read(PresetFile)
			Config = dictionary.deep_merge(BaseConfig, Buffer, uniqueness = True)
		else:
			return ExportResults.Missing

		if StorageFile.exists():
			
			match strategy:
				case ExportStrategies.Skip:
					return ExportResults.AlreadyExists

				case ExportStrategies.Overwrite:
					json.write(StorageFile, Config)
					return ExportResults.Overwtitten

				case ExportStrategies.Merge:
					CurrentConfig: dict = json.read(StorageFile)
					Config = dictionary.deep_merge(Config, CurrentConfig, uniqueness = True)
					json.write(StorageFile, Config)
					return ExportResults.Merged

		json.write(StorageFile, Config)

		return ExportResults.Installed

	def install(self):
		"""
		Устанавливает парсер.

		:raises ParserAlreadyExists: Парсер уже установлен.
		:raises RepositoryError: Репозиторий не найден.
		"""

		if self.is_installed:
			raise exceptions.parsers.ParserAlreadyExists(self.__Name)

		self.path.mkdir(exist_ok = True)

		self.__Parsers.manager.packager.clone(
			directory = self.path,
			remote = self.__Parsers.manager.repositories.get(self.__Name, exception = True)
		)

		self.install_requirements()

	def install_requirements(self):
		"""Устанавливает зависимости, если существует файл _requirements.txt_."""

		RequirementsFile = self.path / "requirements.txt"
		if RequirementsFile.exists():
			self.__Parsers.manager.packager.install_requirements(RequirementsFile)

	@run_before_method("_RequireInstallation")
	def launch(self) -> "BaseSourceOperator":
		"""
		Инициализирует оператор источника.

		:return: Оператор источника.
		:rtype: BaseSourceOperator
		:raises FileNotFoundError: Точка вохода в парсер не найдена.
		"""

		ParserMain = self.path / "__init__.py"

		if not ParserMain.exists():
			raise FileNotFoundError(ParserMain)

		Module = importlib.import_module(f"parsers.{self.__Name}")
		ParserManifest = self.load_manifest()

		return Module.SourceOperator(self.__Parsers.manager.system_objects, ParserManifest)

	@run_before_method("_RequireInstallation")
	def load_manifest(self) -> ParserManifest:
		"""
		Загружает манифест парсера.

		:return: Манифест парсера.
		:rtype: ParserManifest
		:raises FileNotFoundError: Файл манифеста не найден.
		"""

		ManifestFile = self.path / "manifest.json"

		if not ManifestFile.exists():
			raise FileNotFoundError(ManifestFile)
		
		return ParserManifest(self.__Parsers.manager.system_objects, self.__Name)

	@run_before_method("_RequireInstallation")
	def uninstall(self, clear: bool = False):
		"""
		Удаляет парсер.

		:param clear: Указывает, нужно ли удалить временные данные и настройки парсера.
		:type clear: bool
		"""
		
		ElementToRemove: list[Path] = [self.path]

		if clear:
			ElementToRemove += [
				self.__Parsers.manager.system_objects.options.CONFIGS_DIR.value / f"{self.__Name}.json",
				self.__Parsers.manager.system_objects.options.TEMP_DIR.value / self.__Name
			]

		for Element in ElementToRemove:
			if Element.exists():
				if Element.is_dir(): shutil.rmtree(Element)
				else: Element.unlink()

	@run_before_method("_RequireInstallation")
	def update(self, requirements: bool = True, force_mode: bool = False) -> bool:
		"""
		Обновляет парсер.

		:param requirements: Указывает, нужно ли установить зависимости после обновления.
		:type requirements: bool
		:param force_mode: Указывает, перезаписывать ли изменения в репозитории.
		:type force_mode: bool
		:return: Возвращает `True`, если состояние каталога парсера изменилось.
		:rtype: bool
		"""

		if not force_mode and self.__Parsers.manager.packager.has_changes(self.path):
			raise exceptions.parsers.RepositoryError("Local changes detected.")

		IsStateChanged: bool = self.__Parsers.manager.packager.pull(
			repository = self.path,
			remote = self.__Parsers.manager.repositories.get(self.__Name, exception = True),
			force_mode = force_mode
		)

		if IsStateChanged and requirements: self.install_requirements()

		return IsStateChanged

#==========================================================================================#
# >>>>> ОСНОВНОЙ КЛАСС <<<<< #
#==========================================================================================#

class Parsers:
	"""Менеджер парсеров."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def installed(self) -> list[str]:
		"""Список названий установленных парсеров."""

		return os.listdir("parsers")

	@property
	def manager(self) -> "Manager":
		"""Системный менеджер."""

		return self.__Manager

	@property
	def root(self) -> Path:
		"""Путь к корневому модулю всех парсеров."""

		return self.__Root

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, manager: "Manager"):
		"""
		Менеджер парсеров.

		:param manager: Системный менеджер.
		:type manager: Manager
		"""

		self.__Manager = manager

		self.__Root: Path = Path("parsers")
		self.__Root.mkdir(exist_ok = True)

	def get_operator(self, parser_name: str, require_installation: bool = True) -> ParserOperator:
		"""
		Запускает оператор парсера.

		:param parser_name: Имя парсера.
		:type parser_name: str
		:param require_installation: Указывает, проводить ли проверку установки парсера.
		:type require_installation: bool
		:return: Оператор парсера.
		:rtype: ParserOperator
		"""

		if require_installation:
			self.is_installed(parser_name, exception = True)

		return ParserOperator(self, parser_name)

	def is_installed(self, parser_name: str, exception: bool = True) -> bool:
		"""
		Проверяет, установлен ли парсер.

		:param parser_name: Имя парсера.
		:type parser_name: str
		:param exception: Указывает, следует ли выбрасывать исключение при отсутствии парсера.
		:type exception: bool
		:return: Возвращает `True`, если парсер установлен.
		:rtype: bool
		:raises ParserNotFound: Парсер не найден.
		"""

		IsInstalled: bool = parser_name in self.installed

		if not IsInstalled and exception:
			raise exceptions.parsers.ParserNotFound(parser_name)

		return IsInstalled
