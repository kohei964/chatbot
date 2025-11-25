import os
import sqlite3
import pymysql

# 環境変数またはデフォルト設定でDBを選択
USE_MYSQL = os.getenv("USE_MYSQL", "false").lower() == "true"

# MAMPに合わせた設定（.envで上書き可）
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root"),   # MAMP既定
    "database": os.getenv("MYSQL_DATABASE", "chatbot_db"),
    "port": int(os.getenv("MYSQL_PORT", 8889)),        # MAMPは8889
    "unix_socket": os.getenv("MYSQL_UNIX_SOCKET", "/Applications/MAMP/tmp/mysql/mysql.sock"),
}

def get_db_connection():
    """
    USE_MYSQL=true のとき:
      1) ソケットがあれば unix_socket で接続（最優先）
      2) なければ TCP(127.0.0.1:8889) で接続
    それ以外は SQLite(chatbot.db)
    """
    if USE_MYSQL:
        kwargs = dict(
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            connect_timeout=5,
        )
        if os.path.exists(MYSQL_CONFIG["unix_socket"]):
            return pymysql.connect(unix_socket=MYSQL_CONFIG["unix_socket"], **kwargs)
        return pymysql.connect(host=MYSQL_CONFIG["host"], port=MYSQL_CONFIG["port"], **kwargs)
    else:
        conn = sqlite3.connect("chatbot.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    


# データベース初期化（テーブル作成）
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    create_table_query = """
    CREATE TABLE IF NOT EXISTS faq (
        id INT AUTO_INCREMENT PRIMARY KEY,
        question VARCHAR(255) UNIQUE,
        answer TEXT
    )
    """ if USE_MYSQL else """
    CREATE TABLE IF NOT EXISTS faq (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT UNIQUE,
        answer TEXT
    )
    """
    create_log_table_query = """
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_message TEXT,
        bot_response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """ if not USE_MYSQL else """
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_message TEXT,
        bot_response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    cursor.execute(create_table_query)
    cursor.execute(create_log_table_query)
    conn.commit()
    conn.close()


# データベース初期化（テーブル作成）============================================================= DB
