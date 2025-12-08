import { useState } from 'react'
import './App.css'


/*== 「App」コンポーネント ===========================*/
//コンポーネント = 画面に表示する単位
function App() {
  const [messages, setMessages] = useState([ 
    {sender: "bot", text: "お問い合わせ内容を入力してください"} //messages:会話履歴  setMessages() 会話履歴を更新
  ]);
  const [input, setInput] = useState(""); //入力欄(textarea)に入力された文字を管理
  const [isLoading, setLoading] = useState(false); //待機中・メッセージ送信中の状態を管理
  /*== 
  useState(): 画面に反映される状態(state)を管理する変数 
  ===*/

  const API_URL = "http://localhost:5001/chat"; //FlaskのURL

  /*== メッセージ送信処理フォーム送信時のメイン処理 ==*/ 
  const handleSend = async (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    //①ユーザーのメッセージを画面に追加
    const userMessage = {sender: "user", text: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      //②Flaskに POST送信
      const res = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: trimmed,
          user_id: "web", //contact.py の chat()と揃える
        }),
      });

      //③レスポンスがエラー → catchに飛ばす
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      //④Flaskから返ってきたJSONを読む
      const data = await res.json();
      const botText = data.response || "サーバーからのレスポンスが不正です";

      //⑤Botのメッセージを追加
      const botMessage = {
        sender: "bot", 
        text: botText 
      };
      setMessages((prev) => [...prev, botMessage]);

    }catch(error){ //⑥通信エラー時の表示
      console.error("API エラー:", error);
      const errorMessage = {
        sender: "bot",
        text: "サーバーとの通信に失敗しました。時間をおいて再度お試しください",
      };
      setMessages((prev) => [...prev, errorMessage]);
    }finally { //⑦通信終了
      setLoading(false);
    }
  };

/*ここまで編集*/
  /*== 実際表示する部分 ==*/ 
  return (
    <div className="app">
      {/*タイトル*/}
      <h1 className="title">大会チャットボット</h1>

      {/* チャット表示エリア */}
      <div className="chat-window">
        {messages.map((m, idx) => (
          <div key={idx} className={ `message-row ${m.sender === "user" ? "message-user" : "message-bot"}`}>
            <div className="message-bubble">
              {m.text.split("\n").map((line, i) => ( // split("\n") ←改行を反映させる
                <span key={i}>
                  {line}
                </span>
              ))}
            </div>
          </div>
        ))}

        {/* 送信中の時にのみ表示させるメッセージ */}
        {isLoading && (
          <div className="message-row mesage-bot">
            <div className="message-bubble">
              入力内容から内容を作成しています...
            </div>
          </div>
        )}
      </div>

      {/* 入力フォームエリア */}
      <form className="input-area" onSubmit={handleSend}>
        <textarea value={input} onChange={(e) => setInput(e.target.value)} placeholder="例）試合会場はどこですか？" rows={2}/>
        <button type="submit" disabled={isLoading || !input.trim()}>
          {isLoading ? "送信中..." : "送信"}
        </button>
      </form>
    </div>
  );

}

{/* http://localhost:5173/ */}

export default App;

