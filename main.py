import dao_service
import file_manager
import api_service

def main():
    base = dao_service.DataBase(db_name='TESTING_15123')

    files = file_manager.FileManager(base)
    bot = api_service.BotCore(file_manager=files, database=base)
    
    bot.start(no_fall=True)


    '''
    СПИСОК
    # OK: отрисовка обводки не фиксированная ширина, а в зависимости от размера страницы. в процентах.

    # OK: переделать example.json и пикчу на jsoncrack
    # OK: при запросе "vector" Дата: 2025-05-18 02:29:30 
    #          при запросе "типы" Дата: 18.10.2023
    # OK: скачивание файлов.
    # OK: поиск по двум и более словам
    
    # OК: загрузка файлов админами
    # OК: фильтры по тегам!!
    # TODO: переделать report_store?
    # TODO: возможный ложный наход в kmpSearch?
    '''


def test_scenario():
    '''сценарий чтобы добавить файлы в базу данных
    выполнять 1 раз!'''
    base = dao_service.DataBase(db_name='TESTING_15123')
    files = file_manager.FileManager(base)
    files.runPath('./files/')
    print(base)


def cli_database():
    database = dao_service.DataBase(db_name='cli')
    
    while True:
        choice = input('''
1) Создать документ в базе (SAMPLE_LECTURE)
2) Вывести созданный документ
3) Вывести все документы
4) Тест поиска по документу
5) Удалить документ
''')
        
        match choice:
            case '1':
                doc_id = database(dao_service.SAMPLE_LECTURE)
                print('id:', doc_id)
            case '2':
                print(database[doc_id])
            case '3':
                print(database)
            case '4':
                tag_filters = {
                    "tags.course": "3",
                    "tags.filetype": "pdf",
                    "tags.date": { "$gte": "01.01.2024", "$lte": "31.12.2024"}
                }
                database.search('биология', tag_filters)
            case '5':
                del database[doc_id]
            case _:
                print("Выход")
                break

def cli_file_transfer():
    # Инициализация FileManager (без привязки к базе, если не требуется)
    fm = file_manager.FileManager()
    
    while True:
        choice = input('''
Выберите операцию File Transfer:
1) Обработать отдельный файл
2) Обработать директорию
3) Рендер страницы файла в изображение
4) Выход
Ваш выбор: ''')
        
        match choice:
            case '1':
                file_path = input("Введите полный путь к файлу: ").strip()
                result = fm.runFile(file_path)
                print(f"Результат обработки файла: {result}")
            case '2':
                dir_path_input = input("Введите путь к директории: ").strip()
                fm.runPath(dir_path_input)
            case '3':
                file_path = input("Введите путь к файлу для рендера: ").strip()
                page_index_input = input("Введите номер страницы для рендера (оставьте пустым для всех страниц): ").strip()
                page_index = int(page_index_input) if page_index_input else None
                output_path_input = input("Введите путь для сохранения изображения (оставьте пустым для автоматического имени): ").strip() or None
                saved_path = fm.renderToPic(file_path, page_index=page_index, output_path=output_path_input)
                print(f"Изображение сохранено в: {saved_path}")
            case '4':
                print("Выход из cli_file_transfer.")
                break
            case _:
                print("Неверный выбор. Попробуйте снова.")


if __name__ == '__main__':
    #cli_database()
    #cli_file_transfer()

    #test_scenario()
    main()
    