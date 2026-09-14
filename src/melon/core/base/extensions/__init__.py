from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic_core import ValidationError

from .options import BaseExtensionOptions

if TYPE_CHECKING:
	from pathlib import Path

	from ....core.base.parsers.components.settings import (
		CustomSettingsTemplate,
		ParserSettings,
	)
	from ....core.system_objects import SystemObjects
	from ....core.system_objects.printer import Portals
	from ..source_operator import BaseSourceOperator, ParserManifest

class BaseExtension[SO: "BaseSourceOperator", CSM: "CustomSettingsTemplate", EO: BaseExtensionOptions](ABC):
	"""Базовое расширение."""

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def manifest(self) -> "ParserManifest":
		"""Манифест парсера."""

		return self._source_operator.manifest

	@property
	def name(self) -> str:
		"""Имя расширения."""

		return self._name

	@property
	def options(self) -> EO:
		"""Настройки расширения."""

		return self._options

	@property
	def parser_settings(self) -> "ParserSettings[CSM]":
		"""Настройки парсера."""

		return self._source_operator.settings

	@property
	def portals(self) -> "Portals":
		"""Порталы вывода парсера."""

		return self._source_operator.portals

	@property
	def source_operator(self) -> SO:
		"""Оператор источника."""

		return self._source_operator

	@property
	def system_objects(self) -> "SystemObjects":
		"""Коллекция системных объектов."""

		return self._source_operator.system_objects

	@property
	def temp_directory(self) -> "Path":
		"""Путь ко временной директории расширения."""

		return self._temp_directory

	#==========================================================================================#
	# >>>>> НАСЛЕДУЕМЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def _parse_options(self) -> EO:
		"""
		Парсит настройки расширения.

		В случае ошибоки валидации словаря настроек выводит подробности в терминал и завершает работу.

		:return: Настройки расширения.
		:rtype: EO
		"""

		try:
			return self.parser_settings.extensions.get(self._name, self._export_options_model())

		except ValidationError as exception:

			for error in exception.errors():
				error_type: str = error["type"].lower()
				field: str = "/".join(str(key) for key in error["loc"])
				self.portals.printer.error(f"Field <b>{field}</b> error: <i>{error_type}</i>.", origin = self._name)

			self.portals.printer.critical("Unable parse extension options.", end_work = True)

	#==========================================================================================#
	# >>>>> ПЕРЕОПРЕДЕЛЯЕМЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	@abstractmethod
	def _export_options_model(self) -> type[EO]:
		"""
		Возвращает модель опций.

		:return: Модель опций.
		:rtype: type[BaseExtensionOptions]
		"""

		pass

	def _post_init(self):
		"""Метод, выполняющийся после инициализации объекта."""

		pass

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, source_operator: SO):
		"""
		Базовое расширение.

		:param source_operator: Оператор источника.
		:type source_operator: BaseSourceOperator
		:param name: Имя расширения.
		:type name: str
		:raises FileNotFoundError: Каталог расширения не найден.
		"""

		self._source_operator: SO = source_operator
		self._name: str = self.__module__.split(".")[-1]
		
		self._options: EO = self._parse_options()
		self._temp_directory: "Path" = self._source_operator.system_objects.temper.get_extension_temp_directory(self._source_operator.parser_name, self._name)

		self._post_init()