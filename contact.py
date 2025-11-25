from flask import Flask, request, jsonify
from flask_cors import CORS
import os

from dotenv import load_dotenv
load_dotenv()

from bot_core import get_response

from janome.tokenizer import Tokenizer

from db import get_db_connection, init_db, USE_MYSQL
init_db()  #データベース接続

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
    
    user_id = getattr(event.source, "user_id", "unknown")
    user_message = event.message.text #メッセージのテキストを取得
    print(f"受信メッセージ: {user_message}") #デバッグ
    
    chatbot_response = get_response(user_id, user_message) #チャットボットの回答を取得　
    #get_response() は、SQLite または MySQL のデータベースから適切な回答を探す関数
    if chatbot_response is None:
        chatbot_response = "申し訳ありませんが、その質問には対応しておりません。"
    print(f"返信メッセージ: {chatbot_response}") #デバッグ
    
    #LINEに返信
    line_bot_api.reply_message( #返信のために、LINE APIを呼び出す
        event.reply_token,       #LINE の API でメッセージを返信するためのトークン
        TextSendMessage(text=chatbot_response) #ユーザーに送信するテキストメッセージを作成
    )



# ユーザーからの問い合わせを処理
@app.route("/chat", methods=["POST"])  # `method` → `methods` に修正
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
