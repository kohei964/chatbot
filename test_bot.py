import unittest
from handlers import handle_faq
from db import init_db #テスト用DB追加
import sqlite3
import handlers

#ログ保存を無効化
handlers.save_log = lambda *args, **kwargs: None

#ダミー関数(normalize用)
def dummy_normalize(x):
    return x

class TestBot(unittest.TestCase):

    def setUp(self):
        #テスト用DB追加
        #DB初期化
        init_db()

        #map_response作成
        conn = sqlite3.connect("chatbot.db")
        cur = conn.cursor()

        #一旦DB削除
        cur.execute("DROP TABLE IF EXISTS faq")
        cur.execute("DROP TABLE IF EXISTS map_response")


        #テスト用テーブル作成
        cur.execute("""
        CREATE TABLE IF NOT EXISTS map_response (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_date TEXT,
            stadium_name TEXT
        )
        """)

        #テスト用テーブル作成
        cur.execute("""
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            has_map INTEGER DEFAULT 0
        )
        """)

        #テストデータ作成
        cur.execute("""
        INSERT INTO map_response (game_date, stadium_name)
        VALUES ('2026-04-10', '長久手市民球場')
        """)

        cur.execute("""
        INSERT INTO faq (question, answer, has_map)
        VALUES ('試合会場', 'マッチする日程が見つかりませんでした。再度日付を入力し、ご送信くださいませ。', 1)
        """)

        conn.commit()
        conn.close() #DB接続切る

    #日付テスト（ヒットするパターン）
    def test_date_hit(self):
        res = handle_faq(
            user_id="test_user",
            text="4/10の会場は？",
            tone="normal",
            normalize_question=dummy_normalize
        )

        print(res) #デバッグ用
        self.assertIn("会場", res)

    #日付テスト（未登録日）
    def test_no_hit(self):
        res = handle_faq("u", "7/30の会場は？", "normal", dummy_normalize)
        self.assertIn("申し訳", res)

    #日付テスト(日付なし）
    def test_no_date(self):
        res = handle_faq("u", "会場どこ？", "normal", dummy_normalize)
        self.assertIsInstance(res, str)


if __name__ == "__main__":
    unittest.main()
