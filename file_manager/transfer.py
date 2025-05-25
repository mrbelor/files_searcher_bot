from pathlib import Path
from PIL import Image, ImageDraw
from pprint import pprint as pp
from math import sqrt

from .parsers import PdfParser, ImgParser
from .file_manager_configs import ERROR, OK, INFO, OUTLINE_FACTOR, OUTLINE_COLOR, cb


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

class FileManager():
	"""
	- run a file: result = FileManager.runFile(file_path)
	- process a directory: FileManager.runPath(directory_path)
	- render a page to image: image = FileManager.renderToPic(file_path, page_index, output_path)
	- draw a rectangle on image: FileManager.drawRectangle(image_path, coords, output_path, color)
	"""
	def __init__(self, database = None):

		self.workDir = Path.cwd() # дирректория в которой был инициализирован этот объект
		self.database = database
		
		# {'.pdf',	'.docx', '.pptx',	  '.ppt', '.pages'}
		self.parsers = {
			'.pdf': PdfParser(),
			'.png': ImgParser(),
			'.jpg': ImgParser(),
			'.jpeg': ImgParser(),
			'.bmp': ImgParser()
		}
	
	def runFile(self, path):
		print(f'{cb('FileManager.runFile')}: {path}')
		path = Path(path)
		
		# проверка пути
		if not path.exists():
			print(f"FileManager.runFile {ERROR}: {path} - путь НЕ существует!")
			return
		elif not path.is_file():
			print(f"FileManager.runFile {ERROR}: {path} - НЕ файл!")
			return
		
		# выбор обработчика
		parser = self.parsers.get(path.suffix, None)
		if not parser:
			print(f"FileManager.runFile {ERROR}: {path.name} - не поддерживаемый тип файла!")
			return
		
		result = parser.run(path)
		#print(f"{parser.__class__.__name__}")

		if not result:
			print(f'FileManager.runFile {ERROR}: {path.name} ({result=})')
			return result
		else:
			print(f'FileManager.runFile {OK}: {path.name}')
	
		if self.database:
			self.database(result) # создаёт документ в базе
		return result

	def runPath(self, path):
		print(f'FileManager.runPath: {path}')
		directory = Path(path)

		# проверка пути
		if not directory.is_dir():
			print(f"FileManager.runPath {ERROR}: {directory} - НЕ дирректория!")
			return
		elif not directory.exists():
			print(f"FileManager.runPath {ERROR}: {directory} - путь НЕ существует!")
			return
		elif not self.database:
			print(f"FileManager.runPath {INFO}: Не привязана база данных!!!")

		current_extensions = set()
		# цикл по всем ФАЙЛАМ в директории с формированием МНОЖЕСТВА типов файлов
		for file in directory.iterdir():
			if file.is_file() and not file.name.startswith('.'):
				current_extensions.add(file.suffix)
		extentions = self.parsers.keys() & current_extensions
		
		print(f'FileManager.runPath {INFO}: Найденые в папке типы - <{current_extensions}>')
		print(f'FileManager.runPath {INFO}: Из них обрабатываемые типы - <{extentions}>')		
		
		okay_counter = 0
		errors_counter = 0
		#pattern = '*.{' + ','.join(extentions).replace('.', '') + '}'  # формирование шаблона из доступных расширений
		#print(pattern)
		#print(list(directory.rglob(pattern)))

		# цикл обработки файлов
		for ext in extentions:
			pattern = '*' + ext

			for file in directory.rglob(pattern):
				parser = self.parsers[file.suffix]
				result = parser.run(file)
				
				if result:
					print(f'FileManager.runPath {OK}: {file.name}')
					okay_counter += 1
				else:
					print(f'FileManager.runPath {ERROR}: {file.name} ({result=})')
					errors_counter += 1
				
				if self.database:
					self.database(result) # создаёт документ в базе
				else:
					print(f'FileManager.runPath {ERROR}: {file.name} ({result=})')
				
				# сброс на всякий случай
				result = None

		if errors_counter:
			print(f'FileManager.runPath {INFO}: <{okay_counter}/\033[91m{errors_counter}\033[0m> <успешных/\033[91mошибочных\033[0m> файлов')
		else:
			print(f'FileManager.runPath {INFO}: <{okay_counter}> <успешных> файлов')


	def renderToPic(self, file_path, page_index = None, output_path = None, zoom=1.0):
		file_path = Path(file_path)
		#print(f'{cb('FileManager.renderToPic')}: {file_path}')
		
		# проверка пути к файлу
		if not file_path.exists():
			print(f"FileManager.renderToPic {ERROR}: {file_path} - путь НЕ существует!")
			return
		elif not file_path.is_file():
			print(f"FileManager.renderToPic {ERROR}: {file_path} - НЕ файл!")
			return
		elif file_path.suffix not in self.parsers.keys():
			print(f"FileManager.renderToPic {ERROR}: {file_path.name} - не поддерживаемый тип файла!")
			return
		
		# выбор обработчика
		parser = self.parsers[file_path.suffix]
		saved_path = parser.renderToPic(
			file_path = file_path,
			page_index = page_index,
			output_path = output_path,
			zoom = zoom
		)

		#print(f'renderToPic {INFO}: {page_index=} файла {file_path.name} сохранена в "{saved_path}"')
		return saved_path
	
	@staticmethod
	def drawRectangle(image_path, coords, output_path=None, color=OUTLINE_COLOR, zoom=1.0):
		image_path = Path(image_path)
		output_path = Path(output_path) if output_path is not None else None # либо None либо Path
		# print(f'{cb('FileManager.drawRectangle')}: {image_path}')

		img = Image.open(image_path)
		draw = ImageDraw.Draw(img)

		# вычисление целой ширины обводки не меньше 1
		line_width = max(1, int(sqrt(img.width * img.height) * OUTLINE_FACTOR))
		

		# Масштабирование координат с учётом zoom
		def _scale_coords(c, factor):
			if isinstance(c, (int, float)):
				return int(c * factor)
			elif isinstance(c, (list, tuple)):
				return [int(x * factor) for x in c]
			return c
		
		scaled_coords = None
		# (x0, y0, x1, y1) - масштабируем каждую координату
		if len(coords) == 4 and all(isinstance(c, (int, float)) for c in coords):
			scaled_coords = [_scale_coords(coords, zoom)]
		# ((x0,y0), (x1,y0), (x1,y1), (x0,y1)) - масштабируем каждую точку
		elif len(coords) == 4 and all(len(p) == 2 for p in coords):
			scaled_coords = [[_scale_coords(point, zoom) for point in coords]]
		else:
			raise ValueError(f"FileManager.drawRectangle {ERROR}: Некорректный формат координат. Ожидается (x0,y0,x1,y1) или [(x0,y0), (x1,y0), (x1,y1), (x0,y1)]\nПолучено: {coords=}")

		# Отрисовка прямоугольника
		if len(scaled_coords[0]) == 4 and all(isinstance(c, (int, float)) for c in scaled_coords[0]):
			draw.rectangle(scaled_coords[0], outline=color, width=line_width)
			print(f"FileManager.drawRectangle {ERROR}: невозможная ошибка №243124314")
		elif len(scaled_coords[0]) == 4 and all(len(p) == 2 for p in scaled_coords[0]):
			up_line =	[scaled_coords[0][0][0], scaled_coords[0][0][1], scaled_coords[0][1][0], scaled_coords[0][1][1]]
			right_line = [scaled_coords[0][1][0], scaled_coords[0][1][1], scaled_coords[0][2][0], scaled_coords[0][2][1]]
			down_line =  [scaled_coords[0][2][0], scaled_coords[0][2][1], scaled_coords[0][3][0], scaled_coords[0][3][1]]
			left_line =  [scaled_coords[0][3][0], scaled_coords[0][3][1], scaled_coords[0][0][0], scaled_coords[0][0][1]]

			# Рисуем 4 линии для полигона
			draw.line(up_line, fill=color, width=line_width)  # верхняя
			draw.line(right_line, fill=color, width=line_width)  # правая
			draw.line(down_line, fill=color, width=line_width)  # нижняя
			draw.line(left_line, fill=color, width=line_width)  # левая

		if output_path:
			img.save(output_path)
			#  fact_coords = {[up_line, right_line, down_line, left_line]}
			#print(f'FileManager.drawRectangle {OK}: {image_path.name}: {coords=}, {str(output_path)=}')
		else:
			img.show()

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

'''
сделать drawRectanglePage?
типа на входе [пикча, номер, документ с базы]
а на выходе рендер пикчи.
---
наверное не надо, потому что это не будет использваоться в продукте.
ОТДЕЛЬНО рендер нужной страницы
и отдельно отрисовка.

чаще всего будет использоваться обводка одного конкретного слова на одной странице.
TODO: надо подумать над реализацией ЭТОГО сценария.
сделать универсальную строку? (типа чтобы в inline кнопках в результатах было.)

2 варианта:
1) рендер, кеширование, подгрузка позже.
2) хранение ИНФОРМАЦИИ о том что отрендерить и рендерить в момент надобности. пикчи и обводки.
это предпочтительнее, потому что экономит место и поидее проще

результат поиска (массив) состоит из:
СТРАНИЦ РЕЗУЛЬТАТОВ
каждая страница это
1) ID документа в базе.
2) номер страницы в документе. 
3) слово которое нужно найти и обвести.

---
TODO: - ХОТЯ НЕТ!
в любом случае нужно подгрузить все эти результаты.
ты же не будешь заново всё рендерить при каждом перелистывании страницы?

результаты долдны быть названы типа "20250507_780192695_3" дата_id_страница 
уже с отрисованными словами.


---
TIP zoom: 
в pdf парсере есть zoom котоый нигде не учитывается. в особенности в сканере и в DrawRectangle 
добавил учёт в _add_words_from_image 
убрал учёт в _add_words_from_image
zoom должен учитываться ТОЛЬКО в drawRectangle и renderToPic (но никак не в математических вычислениях координат и сканировании)
'''

# тест рабочий
def test_one_pdf_and_render_all_pages_with_outlines():
	fm = FileManager()
	pdf_file = Path('./tests_sources/Компьютерные_сети--20240321-3-2-Лютц_Сергей_Васильевич.pdf')
	render_dir = Path('./hybrid_test/')
	render_dir.mkdir(parents=True, exist_ok=True)

	# Полное сканирование и преобразование в json
	res = fm.runFile(pdf_file)
	if not res: raise Exception(f"почему-то пустой res!!!\n{res=}")

	# Рендер всех страниц PDF
	fm.renderToPic(pdf_file, output_path=render_dir)

	# Отрисовка координат на рендерах
	for index, page in enumerate(res['pages']):
	
		render_path = render_dir / f'img{index}.png'
		for word in page:
			
			fm.drawRectangle(
				image_path=render_path,
				coords=word['coords'],
				output_path=render_path
			)
		print(f'Страница {index}: координаты отрисованы в {render_path}')

	print('Тест завершён!')

# FIXME не работает. под новый формат документов
def choose_one_page_and_render_all_outlines():
	fm = FileManager()
	pdf_file =  Path('./tests_sources/Компьютерные_сети--20240321-3-2-Лютц_Сергей_Васильевич.pdf')
	page_number = 2

	# полное сканирование и преобразование в json
	res = fm.runFile(pdf_file)
	if not res: return

	# рендер конкретной страницы
	fm.renderToPic(pdf_file, page_number, './super_puper_render.png')

	# фильтровка всех слов по номеру желаемой страницы
	page_words = [word for word in res['words'] if word['page'] == page_number]  # word = {"word": "я", "coords": [[269, 127], [368, 127], [368, 142], [269, 142]], "page":0},

	# отрисовка обводки всех слов на странице
	for i in page_words:
		print(i)
		fm.drawRectangle(
			image_path='super_puper_render.png', 
			coords = i['coords'], 
			output_path='super_puper_render.png'
		)


if __name__ == "__main__":
	input('\nДЕМОНСТРАЦИОННЫЙ РЕЖИМ (ТЕСТИРОВАНИЕ) (надо нажимать Enter каждый раз)')
	input('\n ================ ТЕСТ test_one_pdf_and_render_all_pages_with_outlines ================')
	test_one_pdf_and_render_all_pages_with_outlines()
	#input('\n ================ ТЕСТ choose_one_page_and_render_all_outlines ================')
	#choose_one_page_and_render_all_outlines()
	