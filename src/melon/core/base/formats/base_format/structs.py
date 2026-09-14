from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
	from .branch import Branch
	from .chapter import BaseChapter

@dataclass(frozen = True)
class ChapterSearchResult:
	"""Результат поиска главы."""
	
	branch: "Branch"
	chapter: "BaseChapter"

@dataclass(frozen = True)
class ExtraField:
	"""Дополнительное поле данных."""

	after_key: str
	name: str
	value: Any

@dataclass(frozen = True)
class SavingResult:
	"""Результат сохранения тайтла."""

	is_saved: bool
	is_slug_changed: bool
	is_local_file_renamed: bool
	unused_images_removed: int