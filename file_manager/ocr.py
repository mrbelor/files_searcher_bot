import os, pytesseract, requests
import numpy as np
from tqdm import tqdm
from PIL import Image, ImageDraw
from pathlib import Path
from .file_manager_configs import *
# Устанавливаем путь к локальным языковым данным (для tesseract)
os.environ['TESSDATA_PREFIX'] = str(TESSDATA_DIR) 
# !! убедиться что файл откуда взят TESSDATA_DIR находиться в той же директории что и этот файл

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

def download_lang_data():
	"""
	Проверяет наличие файлов tessdata в директории
	Скачивает языковые данные в директорию tessdata
	"""
	TESSDATA_DIR.mkdir(parents=True, exist_ok=True)

	# выяснение наличия требуемых файлов
	existing_files = [f.name for f in TESSDATA_DIR.glob('*.traineddata') if f.is_file()]
	needed_files = [f for f in LANGUAGES.values() if f not in existing_files]
	
	if needed_files:
		print(f"ocr.download_lang_data {INFO}: Некоторые файлы tessdata ОТСУТСТВУЮТ!")
	else:
		print(f"ocr.download_lang_data {OK}: Все языковые файлы существуют.")
		return
	
	for filename in needed_files:
		url = BASE_URL + filename
		local_path = TESSDATA_DIR / filename
		print(f"Скачивание файла {filename}...")
		response = requests.get(url, stream=True)
		total_size = int(response.headers.get('content-length', 0))
		with open(local_path, 'wb') as f, tqdm(
			desc=filename,
			total=total_size,
			unit='iB',
			unit_scale=True,
			unit_divisor=1024,
		) as pbar:
			for data in response.iter_content(chunk_size=1024):
				size = f.write(data)
				pbar.update(size)
	print(f"ocr.download_lang_data <{OK}>: Все требуемые файлы скачаны в директорию {TESSDATA_DIR.name}")

def process_image(image_input):
	"""
	Обрабатывает изображение и возвращает структурированные данные о распознанном тексте
	Args:
		image_input (str, Path, or PIL.Image): путь к файлу, объект Path или уже загруженное изображение
	Returns:
		list: [full_text, [(word: str, coords: tuple), ...]]
	"""
	# проверка и загрузка изображения
	if isinstance(image_input, Path) or isinstance(image_input, str): # совмещённая для Path и str
		pil_img = Image.open(str(image_input))
	elif isinstance(image_input, Image.Image): # для PIL.Image
		pil_img = image_input
	else:
		raise ValueError(f"ocr.process_image <{ERROR}>: Неверный тип входного аргумента (ожидается str, Path или PIL.Image)")

	# Конвертируем изображение в RGB, если оно не в этом формате
	if pil_img.mode != 'RGB':
		pil_img = pil_img.convert('RGB')

	# обработка pytesseract
	data = pytesseract.image_to_data(
		np.array(pil_img),  # Теперь передаем numpy array (требование pytesseract)
		config=r'--oem 1 --psm 3 -l rus+eng',
		output_type=pytesseract.Output.DICT)
	
	# формирование результата из данных pytesseract
	full_text, words_data = "", []
	for word, x, y, w, h in zip(
		data['text'], data['left'], data['top'], data['width'], data['height']):
		if word := word.strip(): # проверка на пустоту с присваиванием
			coords = ((x, y), (x + w, y), (x + w, y + h), (x, y + h)) # абсолютные координаты углов четырехугольника
			full_text += word + " "
			words_data.append((word, coords))

	# list: [full_text, [(word: str, coords: tuple), ...]]
	return [full_text.strip(), words_data]


def main():
	print('ДЕМОНСТРАЦИОННЫЙ РЕЖИМ')
	download_lang_data()
	
	user_input = input('\nНажмите Enter для тестового изображения \nили введите путь к изображению:')
	user_input = user_input or './tests_sources/test.png'
	image_path = Path(user_input)
	if not image_path.exists(): # проверка на существование картинки
		raise FileNotFoundError(f"Файл не найден: {image_path}")

	# основная обработка изображения
	full_text, words_data = process_image(image_path)
	
	# текстовый результат в текстовый файл
	with open('result.txt', 'w', encoding='utf-8') as f:
		f.write(f"Полный текст: {full_text}\n\n")
		for word_data in words_data:
			f.write(f"Слово: {word_data[0]}, Координаты: {word_data[1]}\n")
	print("Результат сохранен в result.txt")

	# визуальный результат в изображение
	image = Image.open(image_path)
	output_image = image.copy()
	draw = ImageDraw.Draw(output_image)

	for word_data in words_data:
		coords = [tuple(coord) for coord in word_data[1]]  # Конвертируем списки в кортежи
		draw.polygon(
			coords,
			outline=(255, 0, 0),  # Красный цвет
			width=2)

	# сохранение изображения
	output_image.save('result_image.png')
	print("Изображение с обводкой сохранено в result_image.png")

	# отображение изображения
	output_image.show()


if __name__ == '__main__':
	main()
