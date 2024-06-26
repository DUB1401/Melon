from dublib.Methods import Cls

def PrintAmendingProgress(message: str, current_state: int, max_state: int):
	"""
	Выводит в консоль прогресс дополнение глав информацией о содержимом.
		message – сообщение из внешнего обработчика;
		current_state – индекс текущей дополняемой главы;
		max_state – количество глав, которые необходимо дополнить.
	"""

	# Очистка консоли.
	Cls()
	# Вывод в консоль: прогресс.
	print(f"{message}\nAmending: {current_state} / {max_state}")

def PrintCollectingStatus(page: int | None):
	"""
	Выводит в консоль прогресс сбора коллекции из каталога.
		page – номер текущей страницы.
	"""

	# Очистка консоли.
	Cls()
	# Преобразование номера страницы в часть сообщения.
	page = f" titles on page {page}" if page else ""
	# Вывод в консоль: прогресс.
	print(f"Collecting{page}...")

def PrintParsingStatus(message: str):
	"""
	Выводит в консоль прогресс дополнение глав информацией о содержимом.
		message – сообщение из внешнего обработчика.
	"""

	# Очистка консоли.
	Cls()
	# Вывод в консоль: прогресс.
	print(f"{message}\nParsing data...")