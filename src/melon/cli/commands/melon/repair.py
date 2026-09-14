from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from dublib.validators import ValidableTypes

from ....core import exceptions
from ....core.base.formats.base_format.enums import By
from ...base.templates import T_SingleParserRequired
from ._base import CommandProcessorTemplate

if TYPE_CHECKING:
	from dublib.cli.terminalyzer import CommandEntity, CommandModel

	from ...base.structs import PreparedData

@dataclass(frozen = True)
class Parameters(T_SingleParserRequired):
	"""Параметры, требуемые обработчиком."""

	filename: str
	target_id: int
	is_target_chapter: bool

class CommandProcessor(CommandProcessorTemplate[Parameters]):
	"""Обработчик команды."""

	#==========================================================================================#
	# >>>>> ПЕРЕОПРЕДЕЛЯЕМЫЕ МЕТОДЫ <<<<< #
	#==========================================================================================#

	@override
	def _build_model(self, model: "CommandModel") -> "CommandModel":
		"""
		Генерирует модель команды.
		
		:param model: Шаблон модели команды.
		:type model: Command
		:return: Модель команды.
		:rtype: CommandModel
		"""

		position = model.create_position("FILE", "Title filename with or without type.", important = True)
		position.set_argument()

		position = model.create_position("TARGET", "Target to repairing.", important = True)
		position.add_key("--branch", value_type = ValidableTypes.UnsignedInteger, description = "Branch ID.")
		position.add_key("--chapter", value_type = ValidableTypes.UnsignedInteger, description = "Chapter ID.")

		self._add_parser_position(key = "--use")
		self._add_mirror_key()

		return model

	@override
	def _export_description(self) -> str:
		"""
		Возвращает описание команды.
		
		:return: Описание команды.
		:rtype: str
		"""

		return "Refrersh chapter content from source."

	@override
	def _parse_parameters(self, entity: "CommandEntity", prepared_data: "PreparedData") -> Parameters:
		"""
		Парсит данные обработанной команды в структуру **dataclass**.

		:param entity: Сущность команды.
		:type entity: CommandEntity
		:param prepared_data: Подготовленные шаблонные параметры команды.
		:type prepared_data: PreparedData
		:return: Структура **dataclass**.
		:rtype: Parameters
		""" 

		filename: str = entity.get_position_value("FILE", expected_type = str, important = True)

		if not filename.endswith(".json"):
			filename += ".json"

		return Parameters(
			required_parser = prepared_data.required_parsers[0],
			filename = filename,
			target_id = entity.get_position_value("TARGET", expected_type = int, important = True),
			is_target_chapter = entity.check_key("--chapter")
		)

	@override
	def _process(self, parameters: Parameters) -> bool:
		"""
		Выполняет команду.

		:param parameters: Параметры, требуемые обработчиком.
		:type parameters: Parameters
		:return: Возвращает `True`, если выполнение успешно и прерывание не требуется.
		:rtype: bool
		"""

		source_operator = self._launch_source_operator(parameters.required_parser)

		if not parameters.is_target_chapter:
			self.printer.error("For now only chapters supported as target to repairing.")
			return False
	
		typing_result = source_operator.get_content_type_by_file(parameters.filename)

		if not typing_result.slug:
			raise exceptions.parsing.ParsingError("Undefined title slug.")

		parser = source_operator.launch_parser(typing_result.content_type)
		title = parser.init_empty_title(typing_result.slug)
	
		if title.load(parameters.filename, By.Filename):
			self.printer.emit(f"Loaded file: <i>{parameters.filename}</i>.")
		else:
			self.printer.error(f"Unable load file: <b>{parameters.filename}</b>.")
			return False
	
		self.printer.emit(f"Repairing chapter <b>{parameters.target_id}</b>… ")
	
		if not parser.repair(parameters.target_id):
			self.printer.warning("Chapter is empty. Repairing failure?")

		saving_result = parser.save()
		self.printer.templates.parsing.saving_result(saving_result)

		return True
