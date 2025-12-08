from flask import Flask, request, jsonify
from flask_cors import CORS
import os

from dotenv import load_dotenv
load_dotenv()

from bot_core import get_response

from janome.tokenizer import Tokenizer

from db import get_db_connection, init_db, USE_MYSQL
init_db()  # データベース初期化

# LINE連携部分
from linebot import LineBotApi, WebhookHandler 
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)
CORS(app)  # CORSを有効化（フロントエンドとの接続）

tokenizer = Tokenizer()

# LINE Botの設定（環境変数 .env からAPI情報を取得）
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "your-access-token")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "your-channel-secret")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# LINE Webhook エンドポイント
@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    
    print(f"受信リクエストボディ：{body}")
    print(f"受信署名：{signature}")
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400
    
    return "OK", 200

# LINEメッセージ処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("メッセージハンドラが実行されました")
    
    user_id = getattr(event.source, "user_id", "unknown")
    user_message = event.message.text
    print(f"受信メッセージ: {user_message}")
    
    chatbot_response = get_response(user_id, user_message)
    if chatbot_response is None:
        chatbot_response = "申し訳ありませんが、その質問には対応しておりません。"
    print(f"返信メッセージ: {chatbot_response}")
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=chatbot_response)
    )

# Web（React）からの問い合わせを処理
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "")
    user_id = data.get("user_id", "web")
    response = get_response(user_id, user_input)
    
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
        query = (
            "INSERT INTO faq (question, answer) VALUES (%s, %s)"
            if USE_MYSQL else
            "INSERT INTO faq (question, answer) VALUES (?, ?)"
        )
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