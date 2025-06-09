import fitz, re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw
from io import BytesIO
from pprint import pprint as pp

from .file_manager_configs import *
# новые алиасы не переименовывают функции!

from .ocr import process_image as ocr_process_image
from .ocr import download_lang_data as ocr_download
ocr_download() # сразу предзагрузка

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


class BaseParser(ABC):
	@abstractmethod
	def run(self, file_path):
		pass
	
	''' 
	# у каждого парсера он свой из-за специфики работы с разными типами
	# НО не у каждого парсера он есть
	@abstractmethod
	def renderToPic(cls, file_path, page_num, output_path):
		pass
	'''

	@classmethod
	def ocrEngine(cls, image): # image - PIL.Image.Image или путь Path
		ocr_text, ocr_words = ocr_process_image(image)
		
		one_words_page = []
		for word, coords in ocr_words:
			one_words_page.append({
				"word": cls.cleanText(word),
				"coords": coords
			})
		return ocr_text, one_words_page
	
	
	@staticmethod
	def _filenameToDict(path:Path):
		# fix макбуковского написания буквы ё (вот так: ё) и буквы й (вот так: й)
		filepath = Path(
			str(Path(path).resolve())
				.replace('и\u0306','й')
				.replace('е\u0308','ё')
		)
		filename = filepath.name


		dateFormat = lambda date_str: datetime.strptime(date_str, "%Y%m%d").strftime("%d.%m.%Y") # date_str '20250313' => '13.03.2025'
		m = FILE_REGEX.match(filename)

		if not m:
			print(f"BaseParser._filenameToDict {ERROR}: REGEX, {m=}, {filename}, {list(filename)=}")
			return {}
		else:
			print(f"BaseParser._filenameToDict {OK}: REGEX, {filename}, {m=}, {m.groups()=}")
		res = {
			"subject": m.group(1) or "",
			"number": m.group(2) or "",
			"date": dateFormat(m.group(3)) if m.group(3) else "", # потому что в lambda нету обработки None
			"course": m.group(4) or "",
			"semester": m.group(5) or "",
			"teacher": m.group(6) or "",
			"doginfo": m.group(7) or "",
			"filetype": f".{m.group(8)}" if m.group(8) else ""  # во избежании ошибки конкотенации с None
		}

		# замена всех _ на пробелы
		for key, value in res.items():
			res[key] = (value or "").replace('_', ' ')

		return res
	
	@staticmethod
	def cleanText(text: str) -> str:
		text = text.lower().replace('ё', 'е')
		text = re.sub(r'[^a-zа-яе0-9 ]', ' ', text)
		text = re.sub(r'\s+', ' ', text) # замена последовательности ' ' на ' '
		return text.strip() # Убираем возможные пробелы в начале и конце строки

	@classmethod
	def initMetadata(cls, path):
		# fix макбуковского написания буквы ё (вот так: ё) и буквы й (вот так: й)
		file_path = Path(
			str(Path(path).resolve())
				.replace('и\u0306','й')
				.replace('е\u0308','ё')
		)

		# проверка аргумента
		if isinstance(file_path, str): # для str
			file_path = Path(file_path)
		elif isinstance(file_path, Path):
			pass
		else:
			raise ValueError(f"BaseParser.initMetadata {ERROR}: Неверный тип входного аргумента file_path - ({type(file_path)}) (ожидается str или Path)")

		# формирование словаря
		return {
		    "filename": file_path.name,
		    "path": str(file_path.resolve()),
		    "tags": cls._filenameToDict(file_path),
		    "len_pages": None,    # будет заполнено числом страниц
		    "text": None,
		    "pages": None         # будет списком списков слов по страницам
		}
	
	


class ImgParser(BaseParser):
	"""
	Класс для парсинга ОДНОГО изображения PNG.
	"""

	def run(self, path):
		# fix макбуковского написания буквы ё (вот так: ё) и буквы й (вот так: й)
		img_path = Path(
			str(Path(path).resolve())
				.replace('и\u0306','й')
				.replace('е\u0308','ё')
		)
		print(f"{cb('ImgParser.run')}: {img_path}")
		

		RESULT_dict = self.initMetadata(img_path) # classmethod можно вызывать и через экземпляр.
		
		ocr_text, ocr_words = self.ocrEngine(img_path) # сканирование с помощью OCR метода

		# приведение к формату (ДАЖЕ если страница всего одна)
		# words = [{"word": i['word'], "coords": i['coords'], "page": 1} for i in words]
		# words = [{"word": i[0], "coords": i[1], "page": 0} for i in words_list] # СТАРАЯ структура документа
		# список из одной страницы со словами (словарями)
		#pages = [[{"word": i[0], "coords": i[1]} for i in ocr_words]] 
		pages = [ocr_words,] # теперь всё в ocrEngine

		
		RESULT_dict['text'] = ocr_text
		RESULT_dict['len_pages'] = 1 # так как изображение - это всегда одна страница 
		RESULT_dict['pages'] = pages
		
		return RESULT_dict # на этом моменте тут сформирован полноценный json документ который уже можно вставлять в БД


class PdfParser(BaseParser):
	"""docstring for PdfParser
	
	run(cls, pdf_path) - метод полностью преобразующий PDF в представление лекции
	renderToPic(cls, pdf_path, page_num, output_path) - метод рендера одной страницы в картинку с поддержкой выбора режимов (все страницы/одна страница)
	_extract_image(cls, doc, block) - метод получения глобальных координат изображения
	_renderToPicServise(cls, page, output_path) - сервисная функция рендера одной страницы в картинку
	"""

	def run(self, path):
		# fix макбуковского написания буквы ё (вот так: ё) и буквы й (вот так: й)
		pdf_path = Path(
			str(Path(path).resolve())
				.replace('и\u0306','й')
				.replace('е\u0308','ё')
		)

		pdf_path = Path(pdf_path)
		print(f"{cb('PdfParser.run')}: {pdf_path}")

		RESULT_dict = self.initMetadata(pdf_path) # classmethod можно вызывать и через экземпляр. 🤯

		doc = fitz.open(str(pdf_path)) # наш документик
		
		all_text = '' # полный сплошной текст с файла
		all_pages = [] # список страниц со словорями 
		'''
		"pages": [
			[
				{"word": "я", "coords": [[269, 127], [368, 127], [368, 142], [269, 142]]},
				{"word": "тим", "coords": [[382, 127], [530, 127], [530, 146], [382, 146]]}
			],
			[
				{"word": "мотоцикл", "coords": [[545, 122], [626, 122], [626, 146], [545, 146]]},
				{"word": "едет", "coords": [[545, 122], [626, 122], [626, 146], [545, 146]]}
			]
		]
		'''

		# глобальная прокрутка ПО СТРАНИЦАМ (итерация = страница)
		for page_index, page in enumerate(doc):
			#pp(inspect.getmembers(page, lambda v: not callable(v)))
			#input("???>")
			current_page_words = []  # список слов на текущей странице (слово - словарик words coords)

			# ================== ТЕКСТ НА СТРАНИЦЕ ==================
			# достаём весь текст сплошняком со станицы
			text_data = page.get_text("text")
			if text_data: 
				all_text += str(text_data) + "\n\n"

			# достаём данные о словах со страницы
			words_data = page.get_text("words")
			for w in words_data:
				x0, y0, x1, y1, word = w[0], w[1], w[2], w[3], w[4]
				current_page_words.append({
						"word": self.cleanText(word),
						"coords": ((x0, y0), (x1, y0), (x1, y1), (x0, y1))  # формат с четырьмя точками
					})

			# ================== ИЗОБРАЖЕНИЯ НА СТРАНИЦЕ ==================
			images = page.get_images(full=True)  # получаем список всех картинок на странице
			
			# print(f"PdfParser.run {INFO}: page_index {page_index}: found {len(images)} images")
			
			# Обрабатываем каждое изображение на странице
			for i in images:
				xref = i[0]  # XREF для извлечения картинки
				base_image = doc.extract_image(xref)  # получаем метаданные картинки
				image_bytes = base_image["image"] # получаем байты картинки из метаданных

				# Загружаем картинку в PIL
				pil_img = Image.open(BytesIO(image_bytes))
				# pil_img.show()

				# OCR и добавление результатов
				ocr_text, ocr_words = self.ocrEngine(pil_img) # list: [full_text:str, [(word: str, coords: tuple), (word: str, coords: tuple), ...]]
				all_text += ocr_text + "\n\n"
				
				# Получаем все рамки (Rect) данного XREF на странице
				rects = page.get_image_rects(xref)  # возвращает список Rect с координатами
				#if len(rects) > 1: print(f'\033[91m<ОЧЕНЬ РЕДКАЯ ОШИБКА №412>\033[0m\n{rects=}')

				if rects:
					pic_box = (rects[0].x0, rects[0].y0, rects[0].x1, rects[0].y1)
				else:
					continue
				
				''' вроде ненужный кусок кода
				if len(rects) > 1:
					print(f"PdfParser.run {INFO}: найдено более одного изображения для xref={xref}")
					for rect in rects:
						print(f"координаты верхнего-левого ({rect.x0:.2f}, {rect.y0:.2f}), "
						  f"нижнего-правого ({rect.x1:.2f}, {rect.y1:.2f})")
				'''
				
				# Перевод координат и добавление слов (не добавление в конец, а конкотенация двух списков на равных условиях)
				current_page_words += self._convert_coords_from_image(
							ocr_words, # list: [(word: str, coords: tuple), (word: str, coords: tuple), ...]
							pic_box,   # tuple: (x0, y0, x1, y1)
							pil_img    # PIL.Image
						)


			# добавлание одного массива/страницы в общий массив страниц
			all_pages.append(current_page_words)
			'''
			"pages": [
				[
					{"word": "я", "coords": [[269, 127], [368, 127], [368, 142], [269, 142]]},
					{"word": "тим", "coords": [[382, 127], [530, 127], [530, 146], [382, 146]]}
				],
				[
					{"word": "мотоцикл", "coords": [[545, 122], [626, 122], [626, 146], [545, 146]]},
					{"word": "едет", "coords": [[545, 122], [626, 122], [626, 146], [545, 146]]}
				]
			]
			'''
		
		# формирование результирующего документа
		RESULT_dict['pages'] = all_pages
		RESULT_dict['text'] = all_text
		RESULT_dict['len_pages'] = len(doc)
		return RESULT_dict

	def _convert_coords_from_image(self, ocr_words, pic_box, pil_image):
		"""
		Математические преобразования координат слов из изображения в глобальные координаты.
		Теперь local_coords — это ((x0, y0), (x1, y0), (x1, y1), (x0, y1)).
		ВСЕГДА четырёхточенчный формат
		"""
		# print(f"PdfParser._convert_coords_from_image: {INFO}: {len(ocr_words)=} {pic_box=} {pil_image=}")
		res_pages_list = [] # список слов с глобальными координатами

		# Распаковываем координаты изображения (pic_box — это (x0_page, y0_page, x1_page, y1_page))
		x0_page, y0_page, x1_page, y1_page = pic_box
		
		# коэффициенты для перевода локальных координат изображения в глобальные
		factor_x = (x1_page - x0_page) / pil_image.width
		factor_y = (y1_page - y0_page) / pil_image.height

		# перевод координат слов из изображения в глобальные
		for word_dict in ocr_words: 
			# Локальные координаты слова в формате ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
			# Нам нужны только (x0, y0) и (x1, y1) — первая и третья точки
			(lx0, ly0), _, (lx1, ly1), _ = word_dict['coords'] # word['coords'] - это ((x0, y0), (x1, y0), (x1, y1), (x0, y1))

			# Вычисляем глобальные координаты с учётом zoom
			global_coords = (
				(x0_page + lx0 * factor_x, y0_page + ly0 * factor_y),  # верхний-левый
				(x0_page + lx1 * factor_x, y0_page + ly0 * factor_y),  # верхний-правый
				(x0_page + lx1 * factor_x, y0_page + ly1 * factor_y),  # нижний-правый
				(x0_page + lx0 * factor_x, y0_page + ly1 * factor_y)   # нижний-левый
			)

			res_pages_list.append({"word": word_dict['word'], "coords": global_coords})
   
		return res_pages_list

	def _renderToPicServise(self, page, output_path, file_path, zoom): 
		# output_path - путь к выходному изображению, file_path - путь к исходному файлу, zoom - коэффициент масштабирования (качества)
		try:
			matrix = fitz.Matrix(zoom, zoom)
			pix = page.get_pixmap(matrix=matrix)
			pix.save(str(output_path))
		except Exception as e:
			print(f"PdfParser._renderToPicServise {ERROR}:\n{str(e)}\n\n<{file_path}> to {output_path}")
		else:
			#print(f"PdfParser._renderToPicServise {OK} to {output_path.relative_to(Path.cwd())}")
			pass
	
	def renderToPic(self, path, page_index=None, output_path=None, zoom=1.0):
		'''docstring for PdfParser.renderToPic
		работает в двух режимах:
		1. если указана страница, то рендерится одна страница
		2. если не указана страница, то рендерится весь документ

		arguments:
			path - путь к файлу (str, Path)
			page_number - номер страницы (int, None) (если не указан, то рендерится весь документ)
			output_path - путь к выходному файлу (str, Path, None) (если не указан, то будет создан в TEMP_FOLDER)
			zoom - коэффициент масштабирования (float, 1.0)
		return:
			output_path - путь к выходному файлу
		'''
		# fix макбуковского написания буквы ё (вот так: ё) и буквы й (вот так: й)
		file_path = Path(
			str(Path(path).resolve())
				.replace('и\u0306','й')
				.replace('е\u0308','ё')
		)

		# Если путь к выходному файлу не указан, выбираем его по умолчанию 
		if not output_path:
			if page_index is not None:
				output_path = Path(TEMP_FOLDER) / f"img{page_index}.png"
			else:
				output_path = Path(TEMP_FOLDER) / file_path.stem # (название папки такое же как и у файла)
		else:
			output_path = Path(output_path)
		
		# наш документик
		doc = fitz.open(str(file_path))

		if page_index is not None: # если страница указана (если page_index != None)
			if output_path.is_dir():
				print(f"PdfParser.renderToPic {ERROR}: ошибка пути <{file_path}> путь ЯВЛЯЕТСЯ ДИРРЕКТОРИЕЙ (ожидался путь к выходному файлу)")
				output_path = output_path / f"img{page_index}.png"
			
			output_path.parent.mkdir(parents=True, exist_ok=True)

			page = doc[page_index]
			self._renderToPicServise(page, output_path, file_path, zoom)

		else: # если страница НЕ указана (нужен весь документ)
			if output_path.is_file(): 
				raise Exception(f"PdfParser.renderToPic {ERROR}: ошибка пути: <{file_path}> путь ЯВЛЯЕТСЯ ФАЙЛОМ (ожидался путь к желаемой папке)")
			
			output_path.mkdir(parents=True, exist_ok=True)

			for idx, page in enumerate(doc):
				img_path = output_path / f'img{idx}.png'
				self._renderToPicServise(page, img_path, file_path, zoom)
		
		print(f"PdfParser.renderToPic: {OK} {file_path.name} [{page_index}] -> {output_path.name}")
		return output_path



# TODO: надо бы сдеалать..
class PptxParser(BaseParser):
	pass

def main():
	#user_input = input('Нажмите Enter для тестового изображения \nили введите путь к изображению:') or png_path

	png_path = './tests_sources/Менеджмент_в_ПД--20240203-3-2-.png'
	pdf_path_img = './tests_sources/Компьютерные_сети--20240321-3-2-Лютц_Сергей_Васильевич.pdf' # pdf из картинок
	pdf_path_text = './tests_sources/Проектирование_и_дизайн-1--3-1-Милехина_Ольга_Викторовна.pdf' # pdf из текста

	input('\nДЕМОНСТРАЦИОННЫЙ РЕЖИМ (ТЕСТИРОВАНИЕ) (надо нажимать Enter каждый раз)')
	ImgPrs = ImgParser()
	pdfPrs = PdfParser()

	input('\n ================ ТЕСТ ImgParser.run() ================')
	res = ImgPrs.run(png_path)
	pp(res)
	print('\nРЕЗУЛЬТАТ: (должен быть сформирован полноценный json документ)')

	input('\n ================ ТЕСТ PdfParser.run() (из изображений) ================')
	res = pdfPrs.run(pdf_path_img)
	pp(res)
	print('\nРЕЗУЛЬТАТ: (должен быть сформирован полноценный json документ)')
	
	input('\n ================ ТЕСТ PdfParser.run() (из текста) ================')
	res = pdfPrs.run(pdf_path_text)
	pp(res)
	print('\nРЕЗУЛЬТАТ: (должен быть сформирован полноценный json документ)')

	input('\n ================ ТЕСТ PdfParser.renderToPic() ================')
	pdfPrs.renderToPic(pdf_path_img)
	print('\nРЕЗУЛЬТАТ: (должна появистя папка с изображениями)')

	input('\n ================ ТЕСТ PdfParser.renderToPic() 1 IMAGE page ================')
	pdfPrs.renderToPic(pdf_path_img, 1)
	print('\nРЕЗУЛЬТАТ: (изображение первой картинки страницы)')

	input('\n ================ ТЕСТ PdfParser.renderToPic() castom page castom name TEXT ================')
	pdfPrs.renderToPic(pdf_path_text, 3, './temp_image_castom_name.png')
	print('\nРЕЗУЛЬТАТ: (изображение третьей текстовой страницы c именем и в корневой папке)')


def _experiment(pdf_path_img):
	pdfPrs = PdfParser()

	res = pdfPrs.run(pdf_path_img)
	pages = res["pages"]
	words = []
	for p in pages:
		for i in p:
			words.append(i["word"])

	print('\n', [w for w in words if ' ' in w])

# в скольких документах есть поле word, в ктором есть хотя-бы один пробел?
def experimentator():
	pdf_dir = Path('../../filesroot/')
	pdf_files = list(pdf_dir.glob('*.pdf'))[:5]

	for pdf_file in pdf_files:
		_experiment(pdf_file)

if __name__ == "__main__":
	main()



