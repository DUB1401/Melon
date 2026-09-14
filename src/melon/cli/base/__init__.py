import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from dublib.cli.terminalyzer import CommandModel

from ...core import exceptions
from ...utils.timer import Timer
from .structs import PreparedData, ProcessorOptions, _InternalStorage

if TYPE_CHECKING:
	from dublib.cli.terminalyzer.commands.group import ModelsGroup
	from dublib.cli.terminalyzer.parser.entitites import CommandEntity

	from ...core.base.source_operator import BaseSourceOperator
	from ...core.system_objects import SystemObjects
	from ...core.system_objects.manager.parsers import ParserOperator
	from ...core.system_objects.printer import Printer
	from .templates import BaseParameters

class BaseCommandProcessor[PARAMS: "BaseParameters"](ABC):
	"""Базовый обработчик команды."""

	_timer: Timer | None

	#==========================================================================================#
	# >>>>> СВОЙСТВА <<<<< #
	#==========================================================================================#

	@property
	def model(self) -> CommandModel:
		"""Модель команды."""

		return self._model

	@property
	def options(self) -> ProcessorOptions:
		"""Настройки обработчика."""

		return self._options

	@property
	def printer(self) -> "Printer":
		"""Оператор вывода."""

		return self._system_objects.printer

	@property
	def system_objects(self) -> "SystemObjects":
		"""Коллекция системных объектов."""

		return self._system_objects

	#==========================================================================================#
	# >>>>> НАСЛЕДУЕМЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def _check_required_parsers(self, parsers_names: tuple[str, ...]):
		"""
		Проверяет наличие требуемых парсеров в системе.

		:param parsers_names: Последовательность имён парсеров.
		:type parsers_names: tuple[str, ...]
		:raises ParserNotFound: Парсер не найден.
		:raises MultipleParsersDeniedForCommand: Команде запрещено использование нескольких парсеров.
		"""

		if not parsers_names:
			return ()

		all_parsers = tuple(self.system_objects.manager.parsers.installed) + self.system_objects.manager.repositories.availabel_parsers

		for parser in parsers_names:
			if parser not in all_parsers:
				raise exceptions.parsers.ParserNotFound(parser)

	def _get_parsers_query(self, entity: "CommandEntity") -> str | None:
		"""
		Возвращает строку, представляющую последовательность имён затребованных парсеров, разделённых запятой.

		По умолчанию берёт данные из позиций `PARSER` или `PARSERS`.
		
		:param entity: Сущность команды.
		:type entity: CommandEntity
		:return: Строка с именами парсеров или `None`, если не требуются.
		:rtype: str | None
		"""

		position_name: str = "PARSERS" if self._internal_storage.is_multiple_parsers_allowed else "PARSER"

		return entity.get_position_value(position_name, expected_type = str, important = False)

	def _end_timer(self):
		"""Выводит результат таймера, если производился отсчёт."""

		if self._timer is not None and not self._internal_storage.is_json_output:
			self.printer.emit(f"Done in {self._timer.ends()}.")

	def _launch_source_operator(self, parser_operator: "ParserOperator") -> "BaseSourceOperator":
		"""
		Запускает оператор контента.
		
		Автоматически применяет зеркало, полученное из ключа `--mirror`, а также кэширует результат для быстрого повторного вызова.

		:param parser_operator: Оператор парсера.
		:type parser_operator: ParserOperator
		:return: Оператор источника.
		:rtype: BaseSourceOperator
		"""

		parser_name: str = parser_operator.name

		if parser_name not in self._internal_storage.source_operators:
			source_operator = parser_operator.launch()
			if self._internal_storage.mirror: source_operator.set_mirror(self._internal_storage.mirror)
			self._internal_storage.source_operators[parser_name] = source_operator
			return source_operator

		return self._internal_storage.source_operators[parser_name]

	def _load_required_parsers(self, data: "CommandEntity") -> tuple["ParserOperator", ...]:
		"""
		Загружает последовательность управляющих структур затребованных парсеров.

		:param data: Сущность команды.
		:type data: CommandEntity
		:return: Последовательность управляющих структур затребованных парсеров.
		:rtype: tuple[ParserOperator, ...]
		:raises exceptions.cli.MultipleParsersDeniedForCommand: Запрашивание нескольких парсеров запрещено.
		"""

		parsers_query: str | None = self._get_parsers_query(data)

		if not parsers_query:
			return ()

		parsers_names = tuple(element.strip() for element in parsers_query.split(","))

		if not parsers_names:
			if self.system_objects.options.DEBUG:
				self.printer.debug("Parsers not selected. All installed will be loaded.")

			parsers_names = tuple(self.system_objects.manager.parsers.installed)

		if not self._internal_storage.is_multiple_parsers_allowed and len(parsers_names) > 1:
			raise exceptions.cli.MultipleParsersDeniedForCommand(data.model.name)

		self._check_required_parsers(parsers_names)

		return tuple(
			self.system_objects.manager.parsers.get_operator(Name, require_installation = False)
			for Name in parsers_names
		)

	def _prepare_parameters(self, entity: "CommandEntity") -> PreparedData:
		"""
		Парсит шаблонные параметры команды.

		:param entity: Сущность команды.
		:type entity: CommandEntity
		:return: Подготовленные шаблонные параметры команды.
		:rtype: PreparedData
		"""

		self._internal_storage.mirror = entity.get_key_value("--mirror", expected_type = str, not_found_error = False)

		return PreparedData(
			required_parsers = self._load_required_parsers(entity),
			force_mode = entity.check_flag("-f"),
			is_json_output = entity.check_flag("-j")
		)

	def _process_safely(self, parameters: PARAMS) -> bool:
		"""
		Оборачивает метод `_process()` для отлова исключений.
		
		:param parameters: Параметры, требуемые обработчиком.
		:type parameters: BaseParameters
		:return: Возвращает `True`, если выполнение успешно и прерывание не требуется.
		:rtype: bool
		"""

		try:
			return self._process(parameters)

		except exceptions.parsers.ParserAlreadyExists as ExceptionData:
			self.printer.error(f"Parser <b>{ExceptionData}</b> already exists.")
			
		except exceptions.parsers.ParserNotFound as ExceptionData:
			self.printer.error(f"Parser <b>{ExceptionData}</b> not found.")

		except exceptions.parsers.RepositoryError as ExceptionData:
			self.printer.error(str(ExceptionData))

		return False

	def _start_timer(self):
		"""Запускает таймер, если разрешено использование настройками обработчика."""

		if self.options.use_timer:
			self._timer = Timer(start = True)

	#==========================================================================================#
	# >>>>> НАСЛЕДУЕМЫЕ МЕТОДЫ ПОСТРОЕНИЯ МОДЕЛЕЙ <<<<< #
	#==========================================================================================#

	def _add_force_mode_flag(self):
		"""Добавляет флаг переключения режима перезаписи."""

		self.model.base.add_flag(
			name = "-f",
			aliases = ("--force",),
			description = "Enable force mode.")

		self._internal_storage.is_force_mode = True

	def _add_json_output_flag(self):
		"""Добавляет флаг включения режима вывода в виде JSON."""

		self._model.base.add_flag(
			name = "-j",
			aliases = ("--json",),
			description = "Prints output as JSON-string."
		)

		self._internal_storage.is_json_output = True

	def _add_parser_position(self, key: str | None = None, description: str | None = None, multiple: bool = False, important: bool = True):
		"""
		Добавляет позицию для имени парсера(ов): `PARSER` или `PARSERS` в зависимости от параметров обработчика.

		:param key: Имя ключа. Если отсутствует, будет использован аргумент.
		:type key: str | None
		:param description: Описание позиции. Если отсутствует, будет использовано стандартное.
		:type description: str | None
		:param multiple: Указывает, разрешена ли загрузка нескольких парсеров.
		:type multiple: bool
		:param important: Указывает, является ли позиция обязательной.
		:type important: bool
		"""

		if multiple:
			self._internal_storage.is_multiple_parsers_allowed = True

			position = self.model.create_position(
				name = "PARSERS",
				description = description or "One or more parsers names separated by comma. By default all.",
				important = important
			)

		else:
			position = self.model.create_position(
				name = "PARSER",
				description = description or "Parser name.",
				important = important
			)

		position.add_key(key) if key else position.set_argument()

	#==========================================================================================#
	# >>>>> ПЕРЕОПРЕДЕЛЯЕМЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	@abstractmethod
	def _build_model(self, model: "CommandModel") -> "CommandModel":
		"""
		Генерирует модель команды.
		
		:param model: Шаблон модели команды.
		:type model: Command
		:return: Модель команды.
		:rtype: CommandModel
		"""

		return model

	@abstractmethod
	def _export_description(self) -> str:
		"""
		Возвращает описание команды.
		
		:return: Описание команды.
		:rtype: str
		"""

		return ""

	def _export_options(self) -> ProcessorOptions:
		"""
		Возвращает настройки обработчика.

		:return: Настройки обработчика.
		:rtype: ProcessorOptions
		"""

		return ProcessorOptions()

	@abstractmethod
	def _parse_parameters(self, entity: "CommandEntity", prepared_data: PreparedData) -> PARAMS:
		"""
		Парсит данные обработанной команды в структуру **dataclass**.

		:param entity: Сущность команды.
		:type entity: CommandEntity
		:param prepared_data: Подготовленные шаблонные параметры команды.
		:type prepared_data: PreparedData
		:return: Структура **dataclass**.
		:rtype: BaseParameters
		"""

		pass

	@abstractmethod
	def _process(self, parameters: PARAMS) -> bool:
		"""
		Выполняет команду.

		:param parameters: Параметры, требуемые обработчиком.
		:type parameters: BaseParameters
		:return: Возвращает `True`, если выполнение успешно и прерывание не требуется.
		:rtype: bool
		"""

		return True

	#==========================================================================================#
	# >>>>> ПУБЛИЧНЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	def __init__(self, system_objects: "SystemObjects", group: "ModelsGroup"):
		"""
		Базовый обработчик команды.

		:param group: Группа, к которой относится модель команды.
		:type group: ModelsGroup
		:param system_objects: Коллекция системных объектов.
		:type system_objects: SystemObjects
		"""

		self._system_objects: "SystemObjects" = system_objects

		self._internal_storage: _InternalStorage = _InternalStorage()
		self._options: ProcessorOptions = self._export_options()
		self._timer: Timer | None = None

		self._model: CommandModel = group.create_model(
			name = self.__class__.__module__.split(".")[-1].split("_")[-1],
			description = self._export_description()
		)
		self._model = self._build_model(self._model)

		self._mirror: str | None = None

	def process(self, entity: "CommandEntity"):
		"""
		Выполняет команду.

		:param entity: Сущность команды.
		:type entity: CommandEntity
		"""

		self._start_timer()

		prepared_data = self._prepare_parameters(entity)
		parameters = self._parse_parameters(entity, prepared_data)

		if not self._process_safely(parameters):
			sys.exit(1)
		
		self._end_timer()
