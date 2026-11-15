import sqlite3, json, threading
from pathlib import Path

class Store:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL, room_id TEXT UNIQUE, name TEXT DEFAULT '', title TEXT DEFAULT '', note TEXT DEFAULT '', group_name TEXT DEFAULT '', quality TEXT DEFAULT 'OD', directory TEXT DEFAULT '', enabled INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recordings(id TEXT PRIMARY KEY, task_id INTEGER, name TEXT, title TEXT, started TEXT, ended TEXT, duration REAL DEFAULT 0, size INTEGER DEFAULT 0, quality TEXT, path TEXT, status TEXT);
        ''')
        self.db.execute("UPDATE recordings SET status='异常中断（需检查文件）' WHERE status='录制中'"); self.db.commit()
    def execute(self, sql, args=()):
        with self.lock:
            try:
                cur = self.db.execute(sql, args); self.db.commit(); return cur
            except Exception:
                self.db.rollback(); raise
    def tasks(self): return [dict(r) for r in self.execute('SELECT * FROM tasks ORDER BY id')]
    def task(self, ident):
        r = self.execute('SELECT * FROM tasks WHERE id=?',(ident,)).fetchone()
        return dict(r) if r else None
    def add(self, url, **values):
        ident = self.execute('INSERT INTO tasks(url) VALUES(?)',(url,)).lastrowid
        if values: self.update(ident, **values)
        return ident
    def update(self, ident, **values):
        allowed = {'room_id','name','title','note','group_name','quality','directory','enabled'}
        if not values or not values.keys() <= allowed: raise ValueError('无效任务字段')
        self.execute('UPDATE tasks SET '+','.join(k+'=?' for k in values)+' WHERE id=?', (*values.values(),ident))
    def setting(self, key, default=None):
        row = self.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default
    def set_setting(self, key, value): self.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,json.dumps(value)))
    def recordings(self, query=''):
        q = '%'+query+'%'
        return [dict(r) for r in self.execute('SELECT * FROM recordings WHERE name LIKE ? OR started LIKE ? ORDER BY started DESC',(q,q))]
    def save_recording(self, item):
        keys = ('id','task_id','name','title','started','ended','duration','size','quality','path','status')
        self.execute('INSERT OR REPLACE INTO recordings VALUES('+','.join('?' for _ in keys)+')', tuple(item.get(k) for k in keys))
    def close(self): self.db.close()
