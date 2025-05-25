import re, json, datetime, cppyy

from pprint import pprint as pp
from pprint import pformat as pf
from pathlib import Path
from pymongo import MongoClient
from bson.objectid import ObjectId
from sys import exit
from shutil import get_terminal_size

from .dao_config import OK, ERROR, INFO, DB_HOST, DB_PORT, DB_NAME, DB_INDEX_NAME, CONN_TIMEOUT, KMP_MODULE_PATH
from .stopwatch import stopWatch as sw

with open(KMP_MODULE_PATH, 'r') as f:
	cppyy.cppdef(f.read())


'''
правила нейминга

переменные - snake_case
константы - UPPER_CASE
классы - PascalCase
функции/методы - camelCase

фикс метки - FIXME
туду метки - TODO

правила вывода в консоль:
{INFO} - информация
{OK} - успех
{ERROR} - ошибка

формат вывода:
<class_name>.<method_name>: <information> # означает запуск метода c доп информацией
<class_name>.<method_name> <INFO/OK/ERROR>: <message> # любое другое сообщение
'''


class JsonHandler:
	# При использовании MongoDB предполагается, что self.collection уже определена
	def exportToJson(self, file_path):
		# Экспорт данных из текущей коллекции MongoDB в JSON файл.
		try:
			documents = list(self.collection.find({}))
			# Преобразуем ObjectId в строку
			for doc in documents:
				doc['_id'] = str(doc['_id'])
		except Exception as e:
			print(f'JsonHandler.exportToJson {ERROR}: {e}')
			return
		with open(file_path, 'w', encoding='utf-8') as file:
			json.dump(documents, file, indent=4)
		print(f'JsonHandler.exportToJson {OK}: collection -> json<{file_path}>')

	def importFromJson(self, file_path):
		# Импорт данных из JSON файла в текущую коллекцию MongoDB.
		try:
			# Читаем данные из JSON файла
			with open(file_path, 'r', encoding='utf-8') as file:
				data = json.load(file)
			# Выполняем массовую вставку документов
			result = self.collection.insert_many(data)
		except Exception as e:
			print(f'JsonHandler.importFromJson {ERROR}: json<{file_path}> -> collection:\n{e}')
			return
		else:
			print(f'JsonHandler.importFromJson {OK}: json<{file_path}> -> inserted {len(result.inserted_ids)} документов')


class UtilityDBTools:

	@staticmethod
	def bytes2Mb(size_bytes, round_digits = 3):
		# Используется двоичное определение: 1 МБ = 1024 * 1024 = 1 048 576 байт.
		megabytes = size_bytes / (1024 * 1024)
		return round(megabytes, round_digits)
	
	@staticmethod
	def unixConfigTime(unix_timestamp):
		# Преобразование Unix timestamp к объекту datetime
		dt = datetime.datetime.fromtimestamp(unix_timestamp)
		# Форматирование времени в строку
		return dt.strftime("%d.%m.%Y")

	@classmethod
	def getTime(cls, path):
		stat = Path(path).stat()
		st_mtime = stat.st_mtime
		st_mtime = cls.unixConfigTime(st_mtime)
		return st_mtime

	@classmethod
	def getSize(cls, path):
		stat = Path(path).stat()
		st_size = stat.st_size
		st_size = cls.bytes2Mb(st_size)
		return st_size
	
	@classmethod
	def getStat(cls, path):
		st_mtime = cls.getTime(path)
		st_size = cls.getSize(path)
		return st_mtime, st_size


	@staticmethod
	def cleanText(text):
		text = text.lower().replace('ё', 'е')
		text = re.sub(r'[^a-zа-яе0-9 ]', ' ', text)
		text = re.sub(r'\s+', ' ', text) # замена последовательности ' ' на ' '
		return text.strip() # Убираем возможные пробелы в начале и конце строки

	@staticmethod
	def _kmpPrefix(needle: list) -> list:
		"""Метод для вычисления префикс-функции (массива lps) для алгоритма Кнута-Морриса-Пратта. 
		Возвращает массив длин наибольших собственных префиксов, которые также являются суффиксами."""
		# lps - longest prefix suffix
		m = len(needle)
		lps = [0] * m
		j = 0
		for i in range(1, m):
			while j and needle[i] != needle[j]:
				j = lps[j - 1]
			if needle[i] == needle[j]:
				j += 1
			lps[i] = j
		return lps
	
	# возможно при использовании "in" будет проблема ложного находа ('br' in 'break'). При условии что в clean_text существует слово "br"
	@classmethod
	def kmpSearch_python(cls, haystack: list, needle: list) -> list:
		"""Поиск подсписка needle в списке haystack алгоритмом Кнута-Морриса-Пратта (KMP).
		Возвращает все стартовые индексы вхождений."""
		n, m = len(haystack), len(needle)
		if m == 0 or n < m: return []
		lps = cls._kmpPrefix(needle)
		res, j = [], 0
		for num, element in enumerate(haystack):
			while j and needle[j] not in element: 
				j = lps[j - 1]
			if needle[j] in element:
				j += 1
				if j == m:
					start = num - m + 1
					res.extend(range(start, start + m)) # добавляем все индексы совпавших элементов
					j = lps[j - 1]
		return res
	
	
	@staticmethod
	def kmpSearch_cpp(haystack: list, needle: list) -> list:
		'''C++ реализация алгоритма Кнута-Морриса-Пратта (KMP) для поиска подсписка needle в списке haystack.'''
		# Прямой вызов C++: list автоматически конвертируется в std::vector<std::string> при передаче в функцию kmpSearch
		res_cpp = cppyy.gbl.kmpSearch(haystack, needle)
		return list(res_cpp)


class DisplayManager:

	@staticmethod
	def _terminal_length(char = None):
		if char is None:
			return get_terminal_size(fallback=(80, 24)).columns
		else:
			return char * get_terminal_size(fallback=(80, 24)).columns

	def showAll_OLD(self):
		"""
		Выводит все документы коллекции с форматированным отображением
		и выводит идентификатор каждого документа.
		"""
		documents = list(self.collection.find({}))
		if not documents:
			print(f'DisplayManager.showAll {ERROR}: В базе нет документов')
		else:
			print(f"DisplayManager.showAll {INFO}: Документы в базе:")

			print(self._terminal_length('-'))
			for doc in documents:
				print(f"Документ <{doc.get('_id', 'ID not found')}>:")
				pp(doc)
				print(self._terminal_length('-'))

	def __bool__(self):
		# я лично использую это для проверки на существование базы данных
		return True
	
	def __str__(self):
		documents = list(self.collection.find({}))
		if not documents:
			return f"DisplayManager.__str__ {ERROR}: В базе нет документов"
		term_line = self._terminal_length('-')
		output_lines = [term_line]

		output_lines.append(f"DisplayManager.__str__ {INFO}: Документы в базе:")
		for doc in documents:
			doc_repr = pf(doc)
			output_lines.append(f"Документ <{doc.get('_id', 'ID not found')}>:")
			output_lines.append(doc_repr)
			output_lines.append(term_line)
		return "\n".join(output_lines)

	def showOne_OLD(self, doc_id):
		"""
		Отображает один документ по его ID.
		Аргументы:
		- doc_id (str): идентификатор документа
		"""
		try:
			doc_id = ObjectId(doc_id)
		except Exception as e:
			print(f'DisplayManager.showOne {ERROR}: Ошибка преобразования ID:\n{e}')
			return

		doc = self.collection.find_one({"_id": ObjectId(doc_id)})
		
		if not doc:
			print(f'DisplayManager.showOne {ERROR}: Документ {doc_id} не найден.')
		else:
			print(self._terminal_length('-'))
			print(f"Документ <{doc.get('_id', 'ID not found')}>:")
			pp(doc)
			print(self._terminal_length('-'))
	
	def showFiltered(self, filter_dict):
		"""
		Отображает документы, удовлетворяющие заданным тегам.

		Аргументы:
		- filter_dict (dict): словарь фильтров, например:
			{
			  "subject": "Психология общения",
			  "number": "1",
			  "date": "27.09.2023",
			  "course": "3",
			  "semester": "1",
			  "teacher": "Ермакова Анна Викторовна",
			  "doginfo": "Античность",
			  "filetype": "pdf"
			}
		"""
		print(f"DisplayManager.showFiltered {INFO} Фильтр: {filter_dict}")
		query = {}
		# Формируем запрос, где каждый фильтр применяется к вложенному полю tags.<key>
		for key, value in filter_dict.items():
			query[f"tags.{key}"] = value
		documents = list(self.collection.find(query))

		
		if not documents:
			print(f"DisplayManager.showFiltered {ERROR}: Нет документов, удовлетворяющих фильтру.")
		else:
			print(f"DisplayManager.showFiltered {INFO}: Найдено {len(documents)} документов, удовлетворяющих фильтру.")
			print(self._terminal_length('-'))
			for doc in documents:
				print(f"Документ <{doc.get('_id', 'ID not found')}>:")
				pp(doc)
				print(self._terminal_length('-'))


	def showCompact(self):
		"""
		Выводит общее количество документов и все записи в чрезвычайно компактном формате,
		показывая только полезную информацию.
		Для компактного вывода используется библиотека 'tabulate', если она установлена.
		"""
		documents = list(self.collection.find({}))
		count = len(documents)
		
		if not documents:
			print(f"DisplayManager.showCompact {ERROR}: Нет документов в базе.")
			return
		else:
			print(f"DisplayManager.showCompact {INFO}: (Всего документов: {count})")
		
		try:
			from tabulate import tabulate
			compact_data = []
			for doc in documents:
				doc_id = doc.get('_id', 'Отсутствует')
				filename = doc.get('filename', 'Не указано')
				tags = doc.get('tags', {})
				subject = tags.get('subject', 'Не указано') if isinstance(tags, dict) else str(tags)
				compact_data.append([doc_id, filename, subject])
			
			headers = ["ID", "Filename", "Subject"]
			print(tabulate(compact_data, headers=headers, tablefmt="grid"))
		
		except ImportError:
			print(f"DisplayManager.showCompact {INFO}: Библиотека 'tabulate' не установлена. Вывод в простом формате:")
			print(self._terminal_length('-'))
			for doc in documents:
				print(f"Документ <{doc.get('_id', 'Отсутствует')}>: Filename: {doc.get('filename', 'Не указано')}, Subject: {doc.get('tags', {}).get('subject', 'Не указано')}")
			print(self._terminal_length('-'))


class DataBase(JsonHandler, UtilityDBTools, DisplayManager):

	def __init__(self, mongo_host=DB_HOST, port=DB_PORT, db_name=DB_NAME, collection_name=DB_INDEX_NAME):
		'''
		- create doc: doc_id = DB(data)
		- search doc: DB.search("searched phrase", {"subject":"Психология общения"})
		- extract one doc: print(DB[doc_id])
		- show all docs: print(DB)
		- delete doc: del DB[doc_id]
		
		- ...
		- show doc in table: DB.showCompact()
		- show doc by filter: DB.showFiltered(filter_dict)
		'''
		# Инициализация подключения к MongoDB и выбор коллекции.
		print(f'DataBase {INFO}: Инициализация DataBase с параметрами: <{mongo_host}:{port}>, {db_name=}, {collection_name=}')
		
		try:
			self.client = MongoClient(mongo_host, port, serverSelectionTimeoutMS=CONN_TIMEOUT)
			self.client.admin.command('ping') # Проверяем подключение к серверу
		except Exception as conn_err:
			print(f'DataBase {ERROR}: Не удалось подключиться к MongoDB по <{mongo_host}:{port}>:\n{conn_err}')
			exit(1)
		
		try:
			self.db = self.client[db_name]
			self.collection = self.db[collection_name]
		except Exception as e:
			print(f'DataBase {ERROR}: Ошибка при инициализации базы данных или коллекции:\n{e}')
			exit(1)
		
		# "прогрев" метода (прекомпиляция)
		self.kmpSearch_cpp(["aaa", "aaa", "aaa", "aaa"],  ["aa", "aa"])

	def __call__(self, data):
		'''
		Создаёт документ и вставляет его в коллекцию MongoDB. 
		Синтаксис: DB(data)
		'''
		try:
			# автоочистка текста
			data['text_clear'] = self.cleanText(data['text'])

			# очистка пустых слов
			for page in data["pages"]:
				page[:] = [item for item in page if item["word"].strip() != ""]

			# если дата не указана, то берём из системы
			if not data['tags'].get('date', None): 
				data['tags']['date'] = self.getTime(data['path'])


			res = self.collection.insert_one(data)
			doc_id = str(res.inserted_id)
		except Exception as e:
			print(f"DataBase.__call__ {ERROR}: {e}")
			return None
		else:
			print(f"DataBase.__call__ {OK}: Документ: {doc_id}")
		return doc_id

	def createDoc(self, data):
		'''
		Создаёт документ и вставляет его в коллекцию MongoDB. 
		Синтаксис: DB.createDoc(data)
		'''
		self(data)

	def __delitem__(self, doc_id):
		'''
		- Удаляет документ из коллекции MongoDB по ID.
		- Cинтаксис: del DB[doc_id]
		'''
		
		try:
			# Проверяем наличие документа по id
			doc = self.collection.find_one({"_id": ObjectId(doc_id)})
			if not doc:
				print(f"DataBase.__delitem__ {ERROR}: Документ {doc_id} не найден.")
				return
		except Exception as e:
			print(f"DataBase.__delitem__ {ERROR}: {e}")
			return

		try:
			self.collection.delete_one({"_id": ObjectId(doc_id)})
			print(f"DataBase.__delitem__ {OK}: Документ {doc_id} удалён.")
		except Exception as e:
			print(f"DataBase.__delitem__ {ERROR}: {doc_id}\n{e}")

	def __len__(self) -> int:
		"""Использует server-side count_documents(), не загружая сами документы в память. """
		return self.collection.count_documents({}) 

	# возврат данных о документе по id
	def __getitem__(self, doc_id):
		"""
		Отображает один документ по его ID.
		Синтаксис: instance[doc_id]
		"""
		try:
			doc_id = str(doc_id).strip()  # Приводим к строке и убираем лишние пробелы (int нельзя)
			doc_oid = ObjectId(doc_id)
		except Exception as e:
			print(f"DisplayManager.__getitem__ {ERROR}: Ошибка преобразования ID:\n{e}")
			return {"message": "Ошибка преобразования ID"}

		doc = self.collection.find_one({"_id": ObjectId(doc_oid)})
		
		if not doc:
			print(f"DisplayManager.__getitem__ {ERROR}: Документ {doc_id} не найден.")
			return {"message": f"Документ {doc_id} не найден."}
		else:
			#line = self._terminal_length('-')
			#formatted_doc = pf(doc)
			#print(f"{line}\nДокумент <{doc['_id']}>:\n{formatted_doc}\n{line}")
			return doc
		
	# в конце класса DataBase (nosql.py)
	def distinct(self, key: str):
		"""
		Возвращает список уникальных значений поля key из всех документов,
		напрямую с помощью MongoDB distinct.
		"""
		try:
			return self.collection.distinct(key)
		except Exception as e:
			print(f"DataBase.distinct {ERROR}:\n{e}")
			return []
	
	def list_compact(self) -> list[str]:
		"""
		Возвращает список строк с краткой информацией о каждом документе:
		ID: filename — subject
		"""
		docs = self.collection.find({}, {"filename": 1, "tags.subject": 1})
		result = []
		for doc in docs:
			doc_id = str(doc["_id"])
			filename = doc.get("filename", "—")
			subject = doc.get("tags", {}).get("subject", "—")
			result.append(f" * {doc_id}: {filename} — {subject}")
		return result
	
	def __iter__(self):
		return iter(self.list_compact())


	

		
	'''
	Общий алгоритм поиска:
	1) берём теги и запрос у пользователя (+чистим запрос)
	2) Mongo фильтрует по tags + по наличию подстроки в text_clear.
	3) далее итеративно по каждому документу:
		далее вложено итеративно по каждой странице документа:
		берём все слова, и сортируем их по полю "coords" 
	(минимальное по x и по y, чтобы однозначно выяснить левый верхний угол) 
	и проходимся по всем словам каким-то эффективным алгоритмом типа kmp
	4) при находе закидываем в отчётный список кортежи с (Mongo_ID, номер страницы, координаты найденного слова)
	'''
	def search(self, phrase, tag_filters=None):
		"""
		Ищет в документе doc точные вхождения фразы phrase.
		Возвращает список словарей с полями:
		- doc_id: идентификатор документа
		- page: номер страницы
		- coords: список координат каждого слова фразы
		"""
		time_point = sw()

		results = []
		tag_filters = tag_filters or {}
		# 1) Очистка и токенизация фразы:
		# оставляем только маленькие а–я, a–z 0-9 и пробелы, приводим к lower() заменяем ё на е
		phrase_clean = re.sub(r'[^a-zа-яе0-9 ]', ' ', phrase.lower().replace('ё', 'е'))
		phrase_tokens = phrase_clean.split()

		
		m = len(phrase_tokens) # длинна needle обычно m
		if m == 0: return []
		
		# 2) Формируем Mongo-запрос: теги + точная фраза в text_clear
		#regex_pattern = r'\b' + r'\s+'.join(re.escape(tok) for tok in phrase_tokens) + r'\b'
		#compiled_regex = re.compile(regex_pattern, re.IGNORECASE | re.UNICODE)
		#query = {**tag_filters, "text_clear": compiled_regex}
		regex_pattern = (
	r'(?:(?<=^)|(?<=[^a-zA-Zа-яё0-9_]))'  # граница начала: начало строки или символ, не являющийся буквой/цифрой
	+ r'\s+'.join(re.escape(tok) for tok in phrase_tokens) +
	r'(?:(?=$)|(?=[^a-zA-Zа-яё0-9_]))'	   # граница конца: конец строки или символ, не являющийся буквой/цифрой
)
		compiled_regex = re.compile(regex_pattern, re.IGNORECASE)
		query = {**tag_filters, "text_clear": compiled_regex}

		cursor = self.collection.find(query)

		# вспомогательные функции для сортировки по "верхнему левому"
		def min_y(tok):
			coords = tok['coords']
			# если первый элемент вложенный (tuple/list), то извлекаем y, иначе предполагаем стандартный формат
			if coords and isinstance(coords[0], (list, tuple)):
				return min(y for _, y in coords)
			else:
				return coords[1]
		
		def min_x(tok):
			coords = tok['coords']
			if coords and isinstance(coords[0], (list, tuple)):
				return min(x for x, _ in coords)
			else:
				return coords[0]


		# 3) Обход всех документов и страниц
		for doc in cursor:
			doc_id = str(doc["_id"])
			for page_num, page_tokens in enumerate(doc.get("pages", []), start=1):
				# 3.1) Сортировка токенов в порядке чтения
				sorted_tokens = sorted(
					page_tokens,
					key=lambda t: (min_y(t), min_x(t))
				)
				words = [t["word"] for t in sorted_tokens]

				# 3.2) Поиск фразы алгоритмом kmp
				positions = self.kmpSearch_cpp(words, phrase_tokens)

				# 4) Сбор координат для страницы, а не для каждого вхождения
				if positions:
					coords_list = []
					for pos in positions:
						# каждая координата берётся как есть, без лишней обёртки
						coords_value = tuple(
							sorted_tokens[pos + i]["coords"] for i in range(m)
						)
						coords_list.append(coords_value[0]) # [0] - обязательно, чтобы избежать лишней вложенности
					consolidated_coords = tuple(coords_list)
					results.append({
						"doc_id": doc_id,
						"page": page_num,
						"coords": consolidated_coords,
						"path": doc["path"]
					})
		
		print(f"DataBase.search {OK}: Поиск '{phrase}'->'{phrase_clean}' ({len(results)}) занял {sw(time_point)}.")
		return results

LINE = lambda: print(DataBase._terminal_length('=')) # просто чтобы линии рисовать  # noqa: E731
SAMPLE_LECTURE_OLD = {

	"filename": "Психология_общения-1-20230927-3-1-Ермакова_Анна_Викторовна@Античность.pdf",
	"path": "/Users/tim/Library/Mobile Documents/com~apple~CloudDocs/Колледж/4 курс/диплом/product/alfa 0.1.2/files root/Психология_общения-1-20230927-3-1-Ермакова_Анна_Викторовна.pdf",
	
	"tags": {
		"subject":"Психология общения",
		"number":"1", # не забыть про _
		"date":"27.09.2023", # сначала берём дату из имени а потом из метаданных
		"course":"3",
		"semester":"1",
		"teacher":"Ермакова Анна Викторовна",
		"doginfo":"Античность",
		"filetype": "pdf"

		#"meantype":"лекция", # +лаба?
	},

	"text":"ehehehe d привет я i тим, я i люблю биологию очень сильно, биология - это жизнь. А ещё Кевин любит биологию. И биологию в интелектуальных системах",
	"text_clear":"",

	"pages": [
		[
			{"word": "ehehehe", "coords": [0, 205, 9, 13]},
			{"word": "d", "coords": [4, 205, 9, 13]},
			{"word": "привет", "coords": [1, 0, 10, 10]},
			{"word": "я", "coords": [2, 0, 20, 10]},
			{"word": "i", "coords": [2, 0, 20, 10]},
			{"word": "тим", "coords": [3, 0, 30, 10]},
			{"word": "я", "coords": [4, 0, 20, 10]},
			{"word": "i", "coords": [4, 0, 20, 10]},
			{"word": "люблю", "coords": [5, 0, 50, 10]}
		],
		[
			{"word": "биологию", "coords": [6, 0, 110, 10]},
			{"word": "очень", "coords": [7, 0, 110, 10]},
			{"word": "сильно", "coords": [8, 0, 110, 10]},
			{"word": "биология", "coords": [9, 0, 110, 10]},
			{"word": "это", "coords": [10, 0, 110, 10]},
			{"word": "жизнь", "coords": [11, 0, 110, 10]}
		],
		[
			{"word": "а", "coords": [12, 0, 110, 10]},
			{"word": "ещё", "coords": [13, 0, 110, 10]},
			{"word": "Кевин", "coords": [14, 0, 160, 10]},
			{"word": "любит", "coords": [15, 0, 160, 10]},
			{"word": "биологию", "coords": [16, 0, 180, 10]},
			{"word": "и", "coords": [17, 0, 180, 10]},
			{"word": "биологию", "coords": [18, 0, 180, 10]},
			{"word": "в", "coords": [19, 0, 180, 10]},
			{"word": "интелектуальных", "coords": [20, 0, 180, 10]},
			{"word": "системах", "coords": [21, 0, 180, 10]}
		]
	]
}


SAMPLE_LECTURE = {

	"filename": "Психология_общения-1-20230927-3-1-Ермакова_Анна_Викторовна@Античность.pdf",
	"path": "/Users/tim/Library/Mobile Documents/com~apple~CloudDocs/Колледж/4 курс/диплом/product/alfa 0.1.2/files root/Психология_общения-1-20230927-3-1-Ермакова_Анна_Викторовна.pdf",
	
	"tags": {
		"subject":"Психология общения",
		"number":"1", # не забыть про _
		"date":"27.09.2023", # сначала берём дату из имени а потом из метаданных
		"course":"3",
		"semester":"1",
		"teacher":"Ермакова Анна Викторовна",
		"doginfo":"",
		"filetype": "pdf"
	},

	"text":"ehehehe d привет я i тим, я i люблю биологию очень сильно, биология - это жизнь. А ещё Кевин любит биологию. И биологию в интелектуальных системах",
	"text_clear":"",

	"pages": [
		[
			{"word": "ehehehe", "coords": ((1510.0, 1017.0), (1512.0, 1017.0), (1512.0, 1028.0), (1510.0, 1028.0))},
			{"word": "d", "coords": ((1461.0, 1031.0), (1512.0, 1031.0), (1512.0, 1044.0), (1461.0, 1044.0))},
			{"word": "привет", "coords": ((1461.0, 1045.0), (1512.0, 1045.0), (1512.0, 1058.0), (1461.0, 1058.0))},
			{"word": "я", "coords": ((1461.0, 1061.0), (1462.0, 1061.0), (1462.0, 1073.0), (1461.0, 1073.0))},
			{"word": "i", "coords": ((1510.0, 1060.0), (1512.0, 1060.0), (1512.0, 1071.0), (1510.0, 1071.0))},
			{"word": "тим", "coords": ((922.0, 1105.0), (1454.0, 1105.0), (1454.0, 1155.0), (922.0, 1155.0))},
			{"word": "я", "coords": ((1457.0, 1104.0), (1674.0, 1104.0), (1674.0, 1143.0), (1457.0, 1143.0))},
			{"word": "i", "coords": ((1129.0, 1143.0), (1189.0, 1143.0), (1189.0, 1156.0), (1129.0, 1156.0))},
			{"word": "люблю", "coords": ((1510.0, 1145.0), (1512.0, 1145.0), (1512.0, 1172.0), (1510.0, 1172.0))}
		],
		[
			{"word": "биологию", "coords": ((1582.0, 1149.0), (1607.0, 1149.0), (1607.0, 1164.0), (1582.0, 1164.0))},
			{"word": "очень", "coords": ((1614.0, 1143.0), (1653.0, 1143.0), (1653.0, 1160.0), (1614.0, 1160.0))},
			{"word": "сильно", "coords": ((1666.0, 1143.0), (1729.0, 1143.0), (1729.0, 1160.0), (1666.0, 1160.0))},
			{"word": "биология", "coords": ((1137.0, 1170.0), (1160.0, 1170.0), (1160.0, 1183.0), (1137.0, 1183.0))},
			{"word": "это", "coords": ((1173.0, 1170.0), (1192.0, 1170.0), (1192.0, 1183.0), (1173.0, 1183.0))},
			{"word": "жизнь", "coords": ((1503.0, 1174.0), (1518.0, 1174.0), (1518.0, 1214.0), (1503.0, 1214.0))}
		],
		[
			{"word": "а", "coords": ((1582.0, 1166.0), (1583.0, 1166.0), (1583.0, 1192.0), (1582.0, 1192.0))},
			{"word": "ещё", "coords": ((1613.0, 1181.0), (1639.0, 1181.0), (1639.0, 1190.0), (1613.0, 1190.0))},
			{"word": "Кевин", "coords": ((1651.0, 1177.0), (1737.0, 1177.0), (1737.0, 1194.0), (1651.0, 1194.0))},
			{"word": "любит", "coords": ((1582.0, 1195.0), (1583.0, 1195.0), (1583.0, 1207.0), (1582.0, 1207.0))},
			{"word": "биологию", "coords": ((1691.0, 1201.0), (1693.0, 1201.0), (1693.0, 1203.0), (1691.0, 1203.0))},
			{"word": "и", "coords": ((1169.0, 1208.0), (1186.0, 1208.0), (1186.0, 1217.0), (1169.0, 1217.0))},
			{"word": "биологию", "coords": ((1198.0, 1204.0), (1238.0, 1204.0), (1238.0, 1217.0), (1198.0, 1217.0))},
			{"word": "в", "coords": ((1262.0, 1204.0), (1270.0, 1204.0), (1270.0, 1217.0), (1262.0, 1217.0))},
			{"word": "интелектуальных", "coords": ((1614.0, 1198.0), (1785.0, 1198.0), (1785.0, 1214.0), (1614.0, 1214.0))},
			{"word": "системах", "coords": ((1700.0, 1194.0), (1730.0, 1194.0), (1730.0, 1220.0), (1700.0, 1220.0))}
		]
	]
}

def test_search(DB):
	print('тест поиска (test_search)')
	
	LINE()
	print("i")
	print(DB.search("i"))

	LINE()
	print("биологию")
	print(DB.search("биологию"))

	LINE()
	print("ehehehe")
	print(DB.search("ehehehe"))

	LINE()
	print("очень сильно")
	print(DB.search("очень сильно"))

	LINE()
	print("ehehehe d")
	print(DB.search("ehehehe d"))

def test_tags_filter_search(DB):
	print('тест фильтрации по тегам (test_tags_filter_search)')
	LINE()

	# 1. Фильтрация по равенству нескольких тегов
	print("Тест 1:\nРавенство (course=3, subject=Психология общения) / поиск 'биологию'")
	tag_filters = {
		"tags.course": "3",
		"tags.subject": "Психология общения"
	}
	print(DB.search("биологию", tag_filters))
	LINE()

	# 2. Поиск по диапазону дат (строковый формат «DD.MM.YYYY»)
	print("Тест 2:\nДиапазон дат (01.01.2024 - 31.12.2024) / поиск 'биологию'")
	tag_filters = {
		"tags.date": {
			"$gte": "01.01.2024",
			"$lte": "31.12.2024"
		}
	}
	print(DB.search("биологию", tag_filters))
	LINE()

	# 3. Несколько значений одного тега ($in)
	print('Тест 3:\n$in (teacher in ["Лютц Сергей Васильевич", "Ермакова Анна Викторовна"]) / поиск "люблю"')
	tag_filters = {
		"tags.teacher": {
			"$in": ["Лютц Сергей Васильевич", "Ермакова Анна Викторовна"]
		}
	}
	print(DB.search("люблю", tag_filters))
	LINE()

	# 4. Регекс-поиск по значению тега (например, по части названия темы)
	print("Тест 4:\n$regex (subject ~ 'общения$') / поиск 'биологию'")
	tag_filters = {
		"tags.subject": {
			"$regex": "общения$",	# заканчивается на «общения»
			"$options": "i"	   # без учёта регистра
		}
	}
	print(DB.search("биологию", tag_filters))
	LINE()

	# 5. Отбор документов, где какой-то тег отсутствует
	print("Тест 5:\nОтсутствие тега (doginfo not exists) / поиск 'биологию'")
	#tag_filters = {
		#"tags.doginfo": { "$exists": False }}
	tag_filters = {"tags.doginfo": ""}
	print(DB.search("биологию", tag_filters))
	LINE()

	# 6. Комбинированный пример
	print("Тест 6:\nКомбинированный фильтр (course=3, filetype=.pdf, date=01.01.2024 - 31.12.2024) / поиск 'биологию'")
	tag_filters = {
		"tags.course": "3",
		"tags.filetype": "pdf",
		"tags.date": {
			"$gte": "01.01.2024",
			"$lte": "31.12.2024"
		}
	}
	print(DB.search("биологию", tag_filters))

def FullTest(DB):

	LINE()
	print("СОЗДАНИЕ")
	doc_id = DB(SAMPLE_LECTURE)

	LINE()
	print("ВЫВОД ОДНОГО")
	print(DB[doc_id])

	print("ВЫВОД ВСЕХ")
	print(DB)
	
	LINE()
	print("ВЫВОД КОМПАКТНО")
	DB.showCompact()

	print(DB._terminal_length('#'))
	print("ПОИСК")
	test_search(DB)


	print(DB._terminal_length('#'))
	print("ПОИСК С ФИЛЬТРАМИ")
	test_tags_filter_search(DB)

	print(DB._terminal_length('#'))

	print("УДАЛЕНИЕ")
	del DB[doc_id]

	#DB.showFiltered(filter_dict)


if __name__ == "__main__":
	DB = DataBase(db_name='example')
	FullTest(DB)
