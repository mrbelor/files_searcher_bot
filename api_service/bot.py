import uuid, telebot, json, os

from telebot.types import Message, CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException
from pathlib import Path
from time import sleep
from signal import signal, SIGINT
from traceback import format_exc as trace
from requests.exceptions import ReadTimeout
from pprint import pformat as pf

from .report_store import UserReportStore
from .markup	   import kb_initial, kb_choose_tag, kb_values, report_keyboard
from .bot_config   import TEXTS, INFO, OK, ERROR, TAG_LABELS, SAVE_FILES_DIR, QUERY_MIN_LIMIT

secrets = json.load(open('secrets.json'))
BOT_TOKEN, ADMIN_IDS = secrets['BOT_TOKEN'], set(secrets['ADMIN_IDS']) # set - на всякий случай. вдруг много админов.

def keyboard(signum, frame):
	exit()
	#raise StopBotException("ctrl+C")
signal(SIGINT, keyboard)


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

class StopBotException(Exception):
	def __init__(self, text='(no reason)'):
		self.text = "manual stop\n" + text

		super().__init__(text)
	def __str__(self):
		return self.text

class BotCore:
	def __init__(self, file_manager, database):
		self.bot = telebot.TeleBot(BOT_TOKEN)
		self.db = database
		self.fm = file_manager
		# хранилище отчётов
		self.store = UserReportStore()


		# --- Хендлеры ---
		@self.bot.message_handler(commands=['start'])
		def start_cmd(m: Message):
			text = TEXTS['start']
			# если админ, добавляем админ текст
			if m.chat.id in ADMIN_IDS: text += "\n\n" + TEXTS['admin_help']
			self.bot.send_message(m.chat.id, text)

		@self.bot.message_handler(commands=['stop'])
		def stop_cmd(m: Message):
			
			if m.chat.id in ADMIN_IDS:
				text = TEXTS['stop']
				self.bot.send_message(m.chat.id, text)
				
				raise StopBotException(f"id админа: {m.chat.id}\nusername админа: @{m.chat.username}")


		@self.bot.message_handler(content_types=['document'])
		def handle_admin_file(m: Message):
			# Игнорируем, если не админ
			if m.chat.id not in ADMIN_IDS:
				return

			# Получаем информацию о файле и скачиваем содержимое
			file_info = self.bot.get_file(m.document.file_id)
			downloaded = self.bot.download_file(file_info.file_path)

			# Формируем путь для сохранения
			save_dir = Path(SAVE_FILES_DIR)
			save_dir.mkdir(parents=True, exist_ok=True)
			save_path = save_dir / m.document.file_name

			# Сохраняем файл на диск
			with open(save_path, 'wb') as f:
				f.write(downloaded)

			# Обрабатываем файл через file_manager
			try:
				doc_id = self.fm.runFile(str(save_path))
				self.bot.reply_to(m, f"Файл проиндексирован: doc_id={doc_id}")
			except Exception as e:
				self.bot.reply_to(m, f"Ошибка при добавлении: {e}")

		@self.bot.message_handler(commands=['del'])
		def del_cmd(m: Message):
			if m.chat.id not in ADMIN_IDS: return

			parts = m.text.strip().split()
			if len(parts) < 2:
				self.bot.reply_to(m, f'{TEXTS["too_few_args"]}\n{TEXTS["/del_usage"]}')
				return
			elif len(parts) > 2:
				self.bot.reply_to(m, f'{TEXTS["too_many_args"]}\n{TEXTS["/del_usage"]}')
				return

			doc_id = parts[1]
			try:
				del self.db[doc_id]
				self.bot.reply_to(m, f"Документ {doc_id} удалён.")
			except KeyError:
				self.bot.reply_to(m, f"Документ {doc_id} не найден.")

		@self.bot.message_handler(commands=['list'])
		def list_cmd(m: Message):
			if m.chat.id not in ADMIN_IDS: return

			lines = self.db.list_compact()
			if not lines:
				text = "В базе нет документов."
			else:
				text = "Все документы в БД:\n" + "\n".join(lines)

			with open("list.txt", "w", encoding="utf-8") as f:
				f.write(text)

			self.bot.send_document(m.chat.id, open("list.txt", "rb"))
			os.remove("list.txt")
		
		@self.bot.message_handler(commands=['change_tag'])
		def change_tag_cmd(m: Message):
			if m.chat.id not in ADMIN_IDS: return

			parts = m.text.strip().split(maxsplit=3)
			if len(parts) < 4:
				self.bot.reply_to(m, f'{TEXTS["too_few_args"]}\n{TEXTS['/change_tag_usage']}')
				return

			_, doc_id, tag_path, new_value = parts
			doc = self.db[doc_id]
			if not doc:
				self.bot.reply_to(m, f"Документ {doc_id} не найден.")
				return
			keys = tag_path.split('.')
			target = doc
			for k in keys[:-1]:
				if k not in target or not isinstance(target[k], dict):
					target[k] = {}
				target = target[k]
			target[keys[-1]] = new_value
			self.db[doc_id] = doc
			report = f"doc['{doc_id}']['{tag_path}'] = '{new_value}'"
			self.bot.reply_to(m, report)
			print(f'BotCore.change_tag_cmd {OK}: {report} от @{m.chat.username} ({m.chat.id})')


		@self.bot.message_handler(commands=['view'])
		def view_cmd(m: Message):
			if m.chat.id not in ADMIN_IDS: return

			parts = m.text.strip().split()
			if len(parts) < 2:
				self.bot.reply_to(m, f'{TEXTS["too_few_args"]}\n{TEXTS['/view_usage']}')
				return
			elif len(parts) > 2:
				self.bot.reply_to(m, f'{TEXTS["too_many_args"]}\n{TEXTS['/view_usage']}')
				return

			_, doc_id = parts
			doc = self.db[doc_id]
			if not doc:
				self.bot.reply_to(m, f"Документ {doc_id} не найден.")
				return

			filename = f"{doc_id}.txt"
			try:
				with open(filename, "w", encoding="utf-8") as f:
					f.write(pf(doc))
				with open(filename, "rb") as f:
					self.bot.send_document(m.chat.id, f)
			except Exception as e:
				self.bot.reply_to(m, f"Ошибка при отправке документа: {e}")
			finally:
				if os.path.exists(filename):
					os.remove(filename)

		@self.bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
		def search_handler(m: Message):
			user_id = str(m.chat.id)
			query = m.text.strip()
			if len(self.db.cleanText(query)) < QUERY_MIN_LIMIT:
				self.bot.send_message(user_id, TEXTS['query_is_small'])
				return
			
			print(f"BotCore.search_handler {INFO}: '{query}' от @{m.chat.username} ({m.chat.id})")
			# 1) сохраняем запрос
			self.store.set_query(user_id, query)
			# 2) создаём новый отчёт
			report_id = str(uuid.uuid4())
			self.store.create_report(report_id, query)
			self.store.set_last_report(user_id, report_id)
			# собираем и показываем клавиатуру с подписью
			current_filters = self.store.get_filters(user_id)
			caption, kb = kb_initial(current_filters)
			self.bot.send_message(user_id, caption, reply_markup=kb)

		@self.bot.callback_query_handler(lambda c: c.data == "search:all")
		def cb_search_all(c: CallbackQuery):
			chat_id = c.message.chat.id
			orig_msg_id = c.message.message_id

			# удаляем сообщение с «Хотите добавить фильтры?»
			self.bot.delete_message(chat_id, orig_msg_id)

			# показываем «песочные часы»
			loading = self.bot.send_message(chat_id, TEXTS["wait"])

			# выполняем поиск без фильтров
			user_id = str(chat_id)
			report_id = self.store.get_last_report(user_id)
			query = self.store.get_query(user_id) or ""
			results = self.db.search(query, {})

			# формируем и отправляем отчёт
			self._do_report(chat_id, report_id, results)

			# убираем «песочные часы»
			self.bot.delete_message(chat_id, loading.message_id)
			self.bot.answer_callback_query(c.id)


		@self.bot.callback_query_handler(lambda c: c.data == "filters:start")
		def cb_filters_start(c: CallbackQuery):
			self.bot.edit_message_text(
				TEXTS["choose_tag"],
				c.message.chat.id,
				c.message.message_id,
				reply_markup=kb_choose_tag()
			)
			self.bot.answer_callback_query(c.id)

		@self.bot.callback_query_handler(lambda c: c.data.startswith("filters:tag:"))
		def cb_choose_tag(c: CallbackQuery):
			tag = c.data.split(":")[-1]
			# просто показываем значения, без ветвления по date
			values = self.db.distinct(f"tags.{tag}")
			kb = kb_values(tag, values)
			self.bot.edit_message_reply_markup(
				c.message.chat.id,
				c.message.message_id,
				reply_markup=kb
			)
			self.bot.answer_callback_query(c.id)


		@self.bot.callback_query_handler(lambda c: c.data.startswith("filters:value:"))
		def cb_set_value(c: CallbackQuery):
			user_id = str(c.message.chat.id)
			parts = c.data.split(":")	 # ["filters","value","<tag>","<idx>"]
			tag = parts[2]
			idx = int(parts[3])

			# берём список значений заново
			values = self.db.distinct(f"tags.{tag}")
			if idx < 0 or idx >= len(values):
				return  # некорректный индекс

			value = values[idx]
			filters = self.store.get_filters(user_id)
			filters[tag] = value
			self.store.set_filters(user_id, filters)

			caption, kb = kb_initial(filters)
			self.bot.edit_message_text(
				caption,
				chat_id=user_id,
				message_id=c.message.message_id,
				reply_markup=kb
			)
			self.bot.answer_callback_query(c.id)


		@self.bot.callback_query_handler(lambda c: c.data == "filters:clear")
		def cb_clear_filters(c: CallbackQuery):
			user_id = str(c.message.chat.id)
			try:
				self.store.clear_filters(user_id)
				caption, kb = kb_initial({})
				self.bot.edit_message_text(caption, user_id, c.message.message_id, reply_markup=kb)
			except ApiTelegramException as e:
				# если сообщение не изменилось — пропускаем
				if "message is not modified" not in str(e):
					raise
			finally:
				self.bot.answer_callback_query(c.id)


		@self.bot.callback_query_handler(lambda c: c.data == "filters:done")
		def cb_filters_done(c: CallbackQuery):
			chat_id = c.message.chat.id
			orig_msg_id = c.message.message_id

			# Удаляем сообщение "Хотите поставить фильтры?"
			self.bot.delete_message(chat_id, orig_msg_id)

			# Посылаем "песочные часы"
			loading = self.bot.send_message(chat_id, TEXTS["wait"])

			# Собираем параметры и делаем поиск
			user_id = str(chat_id)
			report_id = self.store.get_last_report(user_id)
			query = self.store.get_query(user_id) or ""
			uf = self.store.get_filters(user_id)
			tag_filters = {f"tags.{k}": v for k, v in uf.items()}
			results = self.db.search(query, tag_filters)

			# Генерируем и отправляем отчёт
			self._do_report(chat_id, report_id, results)

			# Удаляем сообщение с часами
			self.bot.delete_message(chat_id, loading.message_id)

			# Закрываем «крутилку» в UI Telegram
			try: self.bot.answer_callback_query(c.id)
			except: print(f"BotCore.cb_filters_done {ERROR}??: ошибка при закрытии крутилки {c.id}")

		@self.bot.callback_query_handler(lambda c: c.data == "filters:back")
		def cb_filters_back(c: CallbackQuery):
			chat_id = c.message.chat.id
			# отменяем любой ожидающий шаг (в том числе ввод даты)
			self.bot.clear_step_handler_by_chat_id(chat_id)

			# возвращаем пользователя в основное меню фильтров
			current = self.store.get_filters(str(chat_id))
			caption, kb = kb_initial(current)
			self.bot.edit_message_text(
				caption,
				chat_id=chat_id,
				message_id=c.message.message_id,
				reply_markup=kb
			)
			self.bot.answer_callback_query(c.id)

		# Обработчик «Отмена» – просто удаляет меню фильтров
		@self.bot.callback_query_handler(lambda c: c.data == "filters:cancel")
		def cb_filters_cancel(c: CallbackQuery):
			self.bot.delete_message(c.message.chat.id, c.message.message_id)
			self.bot.answer_callback_query(c.id)

		# --- навигация и отчёт ---
		@self.bot.callback_query_handler(func=lambda c: c.data and c.data.startswith('rep_'))
		def report_nav(c: CallbackQuery):
			_, report_id, pg = c.data.split('_', 2)
			page_idx = int(pg)
			self._send_report(c.message.chat.id, report_id, page_idx, c.message.message_id)
			self.bot.answer_callback_query(c.id)

		@self.bot.callback_query_handler(func=lambda c: c.data == 'noop')
		def noop(c: CallbackQuery):
			self.bot.answer_callback_query(c.id)

		@self.bot.callback_query_handler(lambda cq: cq.data and cq.data.startswith("download:"))
		def callback_download(cq: CallbackQuery):
			_, doc_id = cq.data.split(":", 1)
			path = self.db[doc_id]["path"]
			with open(path, 'rb') as f:
				self.bot.send_document(cq.message.chat.id, f, caption=TEXTS["send_document_caption"])
			self.bot.answer_callback_query(cq.id)





	def _do_report(self, user_id, report_id, results):
		if not results:
			self.bot.send_message(user_id, TEXTS["no_results"])
			return

		# рендерим каждую страницу и сохраняем в store
		for idx, item in enumerate(results):
			# 1) генерируем уникальное имя и путь
			img_name = f"{report_id}_{idx}.png"
			output_path = Path(self.store.img_dir) / img_name

			# 2) рендерим страницу в нужную папку
			self.fm.renderToPic(item["path"], page_index=item["page"] - 1, output_path=output_path)

			# 3) обводим найденные coords, если есть
			for coord in item.get("coords", []):
				self.fm.drawRectangle(output_path, coord, output_path)

			# 4) собираем теги из БД
			tags = self.db[item["doc_id"]]["tags"]

			# 5) сохраняем имя файла и теги в sqlite
			self.store.add_page(report_id, idx, img_name, tags, item["doc_id"])

		# отправляем первую страницу
		self._send_report(user_id, report_id, 0, None)


	def _send_report(self, chat_id, report_id, page_idx, message_id=None):
		page = self.store.get_page(report_id, page_idx)
		if not page:
			return

		# путь до файла на диске
		img_path = Path(self.store.img_dir) / page["img_path"]

		# собираем подпись со ссылкой на запрос и теги
		lines = [
			f'По запросу "{page["query"]}"',
			f'Результат ({page["page_idx"]+1} из {page["total"]}):',
			""
		]
		for key, label in TAG_LABELS.items():
			if page["tags"].get(key):
				lines.append(f"{label}: {page['tags'][key]}")
		caption = "\n".join(lines)

		# клавиатура листания/скачивания
		kb = __import__('api_service.markup', fromlist=['report_keyboard'])\
				.report_keyboard(report_id, page_idx, page["total"], page["doc_id"])

		# отправка или редактирование
		photo = open(img_path, "rb")
		if message_id:
			media = InputMediaPhoto(photo, caption=caption)
			self.bot.edit_message_media(
				media=media,
				chat_id=chat_id,
				message_id=message_id,
				reply_markup=kb
			)
		else:
			self.bot.send_photo(
				chat_id,
				photo=photo,
				caption=caption,
				reply_markup=kb
			)


	def start(self, no_fall=False):
		if not no_fall:
			print(f"BotCore.start {INFO}: polling...")
			self.bot.polling(none_stop=True)
			return

		while True:
			try:
				print(f"BotCore.start {INFO}: polling...")
				self.bot.polling(none_stop=True)

			except StopBotException as e:
				print(e)
				for i in ADMIN_IDS: self.bot.send_message(i, e)
				return

			except ReadTimeout:
				e = 'ReadTimeout'
				print(e)
				for i in ADMIN_IDS: self.bot.send_message(i, e)
				continue

			except Exception:
				tb = trace()
				with open("error.txt", "w", encoding="utf-8") as f:
					f.write(str(tb))
				print(tb)

				sent = False
				while not sent:
					for admin in ADMIN_IDS:
						try:
							self.bot.send_document(admin, open("error.txt", "rb"))
							sent = True
							os.remove("error.txt")
							break
						except:
							print("Не удалось отправить сообщение об ошибке")
					if not sent: sleep(5)
