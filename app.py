from flask import Flask, request, jsonify
from flask_cors import CORS #CORSを有効化
from janome.tokenizer import Tokenizer

app = Flask(__name__)
CORS(app) #CORSを有効化

tokenizer = Tokenizer()

#応答データ
responses = {
    "HP":"HP制作については、詳細をフォームからお問い合わせください",
    "サイト":"HP制作については、詳細をフォームからお問い合わせください",
    "チャットボット":"チャットボット制作については、詳細をフォームからお問い合わせください",
    "時間":"問い合わせ対応時間は、19:00-22:00です。",
    "休み":"対応日は月曜日から土曜日です",
    "いつまで":"納期については、通常は制作開始から2週間〜1ヶ月です。（詳細は打ち合わせにて）",
    "支払い方法":"指定口座への振り込みのみとなります。",
}

def chatbot_response(text):
    tokens = [token.surface for token in tokenizer.tokenize(text)]
    for word in tokens:
        if word in responses:
            return responses[word]
    return "申し訳ありません。その質問には対応していません。"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message","")
    response = chatbot_response(user_input)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)