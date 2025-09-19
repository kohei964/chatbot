from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlite3
import pymysql
import Levenshtein
from dotenv import load_dotenv
load_dotenv()

from janome.tokenizer import Tokenizer

#LINE連携部分
from linebot import LineBotApi, WebhookHandler 
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage


app = Flask(__name__)
CORS(app)  # CORSを有効化（フロントエンドJavaScript などと API を接続


tokenizer = Tokenizer()

#LINE Botの設定（環境変数get.envからAPI情報を取得）
#LINEからメッセージを送るための認証トークン
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "your-access-token")

#Webhookのリクエストを検証するための秘密キー
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "your-channel-secret")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN) #LINEにメッセージを送るためのインスタンス
handler = WebhookHandler(LINE_CHANNEL_SECRET) #LINEから送られてくるメッセージの署名を検証し、イベント処理するためのハンドラー

#LINE Webhook エンドポイント
@app.route("/webhook", methods=["POST"]) #/webhookというエンドポイントを作成、POSTメソッドでリクエストを受信
def webhook():
    signature = request.headers["X-Line-Signature"] #LINEが送信したリクエストの署名を取得（セキュリティ検証）
    body = request.get_data(as_text=True) #リクエストのボディ（メッセージの内容）をテキストとして取得
    
    print(f"受信リクエストボディ：{body}") #デバッグ用
    print(f"受信署名： {signature}") #デバッグ用
    
    try: #エラーが発生する可能性がある時
        handler.handle(body, signature) #上で書いたbody, signatureでLINEから送られたものか検証
    except InvalidSignatureError: #InvalidSignatureErrorが発生した場合
        return "Invalid signature", 400 #HTTP ステータスコード 400 を返す（不正なリクエストとして拒否）
    
    return "OK", 200 #正常に受け取った場合は200”OK”を返す

#LINEメッセージ処理
@handler.add(MessageEvent, message=TextMessage) #ユーザーがLINEでメッセージを送信すると、関数が自動で実行
def handle_message(event):
    
    print(f"メッセージハンドラが実行されました") #デバッグ
    
    user_message = event.message.text #メッセージのテキストを取得
    print(f"受信メッセージ: {user_message}") #デバッグ
    
    chatbot_response = get_response(user_message) #チャットボットの回答を取得　
    #get_response() は、SQLite または MySQL のデータベースから適切な回答を探す関数
    if chatbot_response is None:
        chatbot_response = "申し訳ありませんが、その質問には対応しておりません。"
    print(f"返信メッセージ: {chatbot_response}") #デバッグ
    
    #LINEに返信
    line_bot_api.reply_message( #返信のために、LINE APIを呼び出す
        event.reply_token,       #LINE の API でメッセージを返信するためのトークン
        TextSendMessage(text=chatbot_response) #ユーザーに送信するテキストメッセージを作成
    )


#=== ポート設定 ====
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


init_db()  # 初回実行時にDBを作成


#類似語変換用のシノニム辞書を定義
SYNONYMS = {
    "試合開始時間": ["試合開始","開始","何時から","プレイボール"],
    "試合会場": ["会場","球場","野球場","グラウンド"],
    "日程": ["試合日程","スケジュール"],
    "雨": ["雨天","悪天候","雨が降っていたら","雨だったら","雨天時","雨の場合"],
    "エントリー": ["参加申し込み","申込"],
    "試合球": ["ボール","試合球は"],
    "緊急連絡先": ["連絡先"]
}

#シノニムを正規化する関数（質問を変換）
def normalize_question(text):
    for key, synonyms in SYNONYMS.items():
        for synonym in synonyms:
            if synonym in text:
                return key #正規化されたキーワードを返す
    return text #該当なしならそのまま



def get_response(text):
    # --- 挨拶対応 ---
    greetings = ["こんにちは", "おはようございます", "こんばんわ", "お疲れ様です", "お世話になります"]
    response = None
    for greeting in greetings:
        if greeting in text:
            response = f"{greeting}！いつもありがとうございます。"
            break  # ここでは return しない（最後に共通のログ保存を通す）

    if response is None:
        # --- シノニム正規化 ---
        user_input = normalize_question(text)

        # --- FAQ検索 ---
        conn = get_db_connection()
        cursor = conn.cursor()
        best_match = None
        highest_similarity = 0.0

        try:
            query = "SELECT question, answer FROM faq"
            cursor.execute(query)
            results = cursor.fetchall()

            for row in results:
                # MySQL と SQLite での取得形式の差異を吸収
                db_question = row["question"] if USE_MYSQL else row[0]
                db_answer   = row["answer"]   if USE_MYSQL else row[1]

                # 類似度計算
                similarity = Levenshtein.ratio(user_input, db_question)
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = db_answer

        except Exception as e:
            print(f"Error: {e}")
        finally:
            conn.close()

        # --- 応答決定（ここで return しない）---
        if highest_similarity >= 0.6:
            response = best_match
        else:
            response = "申し訳ありませんが、その質問には対応しておりません。後ほど担当者から返信いたします"

    # --- ここから共通のログ保存（毎回通る）---
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        insert_log_query = (
            "INSERT INTO chat_logs (user_message, bot_response) VALUES (%s, %s)"
            if USE_MYSQL else
            "INSERT INTO chat_logs (user_message, bot_response) VALUES (?, ?)"
        )
        cursor.execute(insert_log_query, (text, response))
        conn.commit()
    except Exception as e:
        print(f"ログ保存エラー: {e}")
    finally:
        conn.close()

    # --- 最後に返す ---
    return response

# ユーザーからの問い合わせを処理
@app.route("/chat", methods=["POST"])  # `method` → `methods` に修正
def chat():
    data = request.get_json()
    user_input = data.get("message", "")
    
    response = get_response(user_input)
    if response:
        return jsonify({"response": response})
    
    return jsonify({"response": "その質問にはまだ対応していません。回答を入力してください。"})


# 回答をデータベースに追加
@app.route("/add_answer", methods=["POST"])
def add_answer():
    data = request.get_json()
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()
    
    if not question or not answer:
        return jsonify({"error": "質問と回答の両方を入力してください。"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "INSERT INTO faq (question, answer) VALUES (%s, %s)" if USE_MYSQL else "INSERT INTO faq (question, answer) VALUES (?, ?)"
        cursor.execute(query, (question, answer))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"データの追加に失敗しました: {e}"}), 500
    finally:
        conn.close()
    
    return jsonify({"message": "回答を追加しました！"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
