# files_searcher_bot

🚀 Мощный телеграм бот, который поможет вам эффективно искать по содержимому файлов.
## Цель проекта
Проект стремится решить проблему утомительного поиска данных в содержимому файлов, предоставляя удобный интерфейс телеграм бота. 
Целевой аудиторией этого проекта являются разработчики и члены команды, которым часто трудно найти определенные файлы в больших базах.

## Особенности и функционал
💡 Основные возможности:
* 🔍 Функция поиска по содержимому файлов (включая изображения)
* 📊 Настраиваемые фильтры поиска

## Примеры использования

<img src="https://i.postimg.cc/3xdrFGY5/image.png" alt="Пример поиска" width="450px"/>

<img src="https://i.postimg.cc/mDXB9ZJ2/image.png" alt="Настройка фильтров" width="450px"/>

Общие инструкции по использованию 📝:
1. Введите поисковый запрос в боте телеграм
2. Настройте фильтры поиска, нажмите "Готово"

## Структура

Проект содержит 3 python пакета:
`dao_service`, `file_manager`, `api_service`

Собранные в один сервис:
```python
import dao_service
import file_manager
import api_service

def main():
    base = dao_service.DataBase(db_name='main')

    files = file_manager.FileManager(base)
    bot = api_service.BotCore(file_manager=files, database=base)

    bot.start(no_fall=True)
```

## ПОЛНЫЙ ТУТОРИАЛ ПО ВСЕЙ КОДОВОЙ БАЗЕ:

[code2tutorial.com](https://code2tutorial.com/tutorial/7a4f7f7f-d358-45b4-bbbc-d171ecd2d7b3/index.md)

## Установка и настройка Телеграм Бота

🔧 Предварительные требования:
* Установлен Python версии 3.8 или выше
* Установлен pip

🔧 Пошаговые инструкции по установке:
1. Клонировать репозиторий
2. Установите необходимые зависимости с помощью pip
   `pip install -r requirements.txt`
3. Создайте в корне файл `secrets.json` в котором напишите api своего бота из `@BotFather`
   и ваш телеграм id (по желанию)
в виде:
```json
{
  "BOT_TOKEN": "TELEGRAM_API",
  "ADMIN_IDS": [1234567]
}
```
4. Проиндексировать нужные вам файлы (один раз)
```python
base = dao_service.DataBase(db_name='main')
files = file_manager.FileManager(base)
files.runPath('./path_to_files_dirrectory/')
```
4. Запустить `python main.py`
5. Теперь им можно пользоваться через telegram бота!

## Стек технологий
Языки:
* Python
* C++
* Shell

## Информация о лицензии

💡 Лицензия:
Этот проект лицензирован по лицензии MIT

⭐ Важное примечание:
Этот проект все еще находится в разработке и может быть нестабильным. Используйте на свой страх и риск.

Наслаждайтесь использованием files_searcher_bot! 💻
