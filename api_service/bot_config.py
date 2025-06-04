
QUERY_MIN_LIMIT = 3
SAVE_FILES_DIR = "./files/"

# color
INFO = "\033[96m<INFO>\033[0m"
OK = "\033[92m<OK>\033[0m"
ERROR = "\033[91m<ERROR>\033[0m"


TAG_LABELS = {
    "subject"  : "Предмет",
    "course"   : "Курс",
    "semester" : "Семестр",
    "number"   : "Номер лекции",
    "date"     : "Дата",
    "teacher"  : "Преподаватель",
    "doginfo"  : "Подпись",
}

# Строки для ответов
TEXTS = {
    "start": "Привет! Я поисковый бот.\nПросто пришли мне слово или фразу - и я найду её в документах.",
    "stop" : "Остановка . . .",
    "no_results": "По вашему запросу ничего не найдено.",
    "admin_help": (
        "⚙ Вы в режиме администратора.\n"
        "Используйте команды:\n"
		"/list                - показать список документов\n"
        "<файл>               - вручную добавить файл в индексацию\n"
        "/del <doc_id>        - удалить документ из БД\n"
        "/change_tag <doc_id> - изменение любого поля документа\n"
        "/view <doc_id>       - просмотр любого документа"
    ),
	# Шаблон страницы
    "page_format": "{current}/{total}",
	
    'previous_button':"⬅️",
	'next_button':"➡️",
	'noop_button':" ",
	'download_button':"Скачать файл",
	
    "send_document_caption":"Документ",
    "query_is_small" : f"Cлишком короткий запрос!\n(минимум {QUERY_MIN_LIMIT} буквы)",
    "too_many_args" : "Ошибка: слишком много аргументов.",
    "too_few_args" : "Ошибка: слишком мало аргументов.",
    "/change_tag_usage" : '/change_tag <id документа> <имя тега> <новое значение>',
    "/del_usage" : '/del <id документа>',
    "/view_usage" : '/view <id документа>'
    
}

# фильтры
TEXTS.update({
    "ask_filters":     "Хотите добавить к запросу фильтры?\nДействующие:\n{current}",
    "search_all":      "🔍 По всей базе",
    "add_filters":     "⚙️ Фильтры",
    "clear_filters":   "🧹 Очистить",
    "choose_tag":      "Выберите параметр для фильтрации:",
    "enter_value":     "Введите значение «{label}»:",
    "enter_date_range":"Введите диапазон дат DD.MM.YYYY-DD.MM.YYYY",
	"wrong_date_format":"❗Неверный формат даты. Используйте DD.MM.YYYY-DD.MM.YYYY",
    "done":            "✅ Готово",
	"back":            "⬅️ Назад",
    "cancel":          "❌ Отмена",
	"wait":            "⌛️",
	"empty_filters":   "Пусто",
})



