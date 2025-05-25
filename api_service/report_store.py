# api_service/report_store.py
import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime

class UserReportStore:
    def __init__(self, db_path = None, img_dir = None):
        self.cfd = Path(__file__).resolve().parent
        self.db_path = db_path or self.cfd / "reports.db"
        self.img_dir = img_dir or self.cfd / "reports_imgs"

        self.db_path.parent.mkdir(parents=True, exist_ok=True) # на всякий случай, вдруг при иницализации указано было.
        self.img_dir.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        c = self.conn.cursor()
        # табличка отчётов
        c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
          id TEXT PRIMARY KEY,
          query TEXT,
          created_at TEXT
        )''')
        # табличка страниц: ХРАНИМ ТОЛЬКО ИМЯ ФАЙЛА
        c.execute('''
        CREATE TABLE IF NOT EXISTS pages (
          report_id TEXT,
          page_idx INTEGER,
          img_name TEXT,
          tags_json TEXT,
          doc_id TEXT,
          PRIMARY KEY(report_id, page_idx)
        )''')

        # таблица для хранения фильтров и последнего запроса пользователя
        c.execute('''
        CREATE TABLE IF NOT EXISTS users_data (
            user_id TEXT PRIMARY KEY, 
            filters_json TEXT,
            last_query TEXT,
            last_report_id TEXT
        )''')
        
        self.conn.commit()

    # --- операции с last_query ---
    def set_query(self, usr_id: str, query: str):
        # Вставляем новую запись или обновляем last_query при совпадении user_id
        self.conn.execute('''
            INSERT INTO users_data(user_id, last_query)
            VALUES(?, ?)
            ON CONFLICT(user_id) DO UPDATE
              SET last_query = excluded.last_query
            ''',
            (str(usr_id), query)
        )
        self.conn.commit()
    
    def get_query(self, usr_id):
        c = self.conn.execute(
            'SELECT last_query FROM users_data WHERE user_id = ?',
            (str(usr_id),)
        )
        row = c.fetchone()
        # Если пользователь ещё не записан, вернём None, иначе сам запрос
        #print(f"{row=} {usr_id=}")
        return row[0] if row[0] else None
    
    # --- методы операции с фильтрами ---
    def set_filters(self, user_id: str, filters: dict):
        fjson = json.dumps(filters, ensure_ascii=False)
        self.conn.execute('''
        INSERT INTO users_data(user_id, filters_json)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE 
          SET filters_json=excluded.filters_json
        ''', (user_id, fjson))
        self.conn.commit()

    def get_filters(self, user_id: str) -> dict:
        res = self.conn.execute('''
            SELECT filters_json FROM users_data 
            WHERE user_id=?''', 
            (str(user_id),))
        row = res.fetchone()
        return json.loads(row[0]) if row[0] else {}

    def clear_filters(self, user_id: str):
        # обнуление фильтров
        self.conn.execute('''
        UPDATE users_data 
        SET filters_json=NULL 
        WHERE user_id=?''', 
        (user_id,))

        self.conn.commit()
    
    #get_user_filters = get_filters
    #set_user_filters = set_filters
    #clear_user_filters = clear_filters

    def create_report(self, report_id: str, query: str):
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            'INSERT INTO reports(id, query, created_at) VALUES(?,?,?)',
            (report_id, query, now)
        )
        self.conn.commit()

    def add_page(self, report_id: str, page_idx: int, img_name: str, tags: dict, doc_id: str):
        """
        img_name – лишь имя файла (например, 'a1b2-... .png').
        Полный путь = os.path.join(self.img_dir, img_name)
        """
        tags_json = json.dumps(tags, ensure_ascii=False)
        self.conn.execute(
            'INSERT OR REPLACE INTO pages(report_id, page_idx, img_name, tags_json, doc_id) VALUES(?,?,?,?,?)',
            (report_id, page_idx, img_name, tags_json, doc_id)
        )
        self.conn.commit()

    def get_page(self, report_id: str, page_idx: int): # FIXME: структура громоздкая, переделать, упростить и достичь быстрой подгрузки при перелистывании
        c = self.conn.cursor()
        # получаем имя картинки и теги
        c.execute(
            'SELECT img_name, tags_json, doc_id FROM pages WHERE report_id=? AND page_idx=?',
            (report_id, page_idx)
        )
        row = c.fetchone()
        if not row: return None

        img_name, tags_json, doc_id = row
        tags = json.loads(tags_json)

        # общее число страниц
        c.execute(
            'SELECT COUNT(*) FROM pages WHERE report_id=?',
            (report_id,)
        )
        total = c.fetchone()[0]

        # теперь вытягиваем query из reports
        c.execute(
            'SELECT query FROM reports WHERE id=?',
            (report_id,)
        )
        qr = c.fetchone()
        query = qr[0] if qr else ""

        return {
            "img_path": os.path.join(self.img_dir, img_name),
            "tags": tags,
            "page_idx": page_idx,
            "total": total,
            "query": query,
            'doc_id': doc_id
        }
    

    def set_last_report(self, user_id: str, report_id: str):
        self.conn.execute('''
            INSERT INTO users_data(user_id, last_report_id)
            VALUES(?, ?)
            ON CONFLICT(user_id) DO UPDATE 
              SET last_report_id=excluded.last_report_id''', 
            (user_id, report_id))
        self.conn.commit()

    def get_last_report(self, user_id: str) -> str:
        c = self.conn.execute(
          'SELECT last_report_id FROM users_data WHERE user_id=?',
          (user_id,)
        )
        row = c.fetchone()
        return row[0] if row[0] else ""
    
