##======================
# 分岐後（intent.py後の処理）
# =====================

import Levenshtein
import re
from db import get_db_connection, USE_MYSQL

from textgen import natural_text
from analysis import reply_for_angry
from context import USER_CONTEXT, SESSION, suggest_labels, make_choice_message, SUGGEST_POOL
from map import make_map_url

#======
#ログ保存の共通部分
#======
def save_log(user_message: str, bot_response: str):
    #ログ保存(共通化)
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        q = (
            "INSERT INTO chat_logs (user_message, bot_response) VALUES (%s, %s)"
            if USE_MYSQL else
            "INSERT INTO chat_logs (user_message, bot_response) VALUES (?, ?)"
        )
        cur.execute(q, (user_message, bot_response))
        conn.commit()
    except Exception as e:
        print(f"ログ保存エラー: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

#======
#自然言語化＋怒り判定時の部分
#======
def apply_style(tone: str, base_response: str, *, opener=True, closer=True) -> str:
    """tone + 自然言語化(共通化)"""
    if tone in ("angry", "insult"):
        core = reply_for_angry(tone, base_response)
        return natural_text(core, use_opener=False, use_closer=closer)
    return natural_text(base_response, use_opener=opener, use_closer=closer)

#======
#繰り返しの質問用部分
#======
def handle_repeat(user_id: str, text: str, tone: str) ->str:
    ctx = USER_CONTEXT[user_id]
    if ctx.get("last_answer"):
        response = apply_style(tone, ctx["last_answer"])
    else:
        response = "直前の会話がありません。お手数ですが、もう一度質問してください"
    
    save_log(text, response)
    return response

#======
#日本語か英語かの部分？
#======
def handle_non_ja(user_id: str, text: str, tone: str) -> str:
    base = "恐れ入りますが、\n日本語でのお問い合わせをお願いいたします。"
    response = apply_style(tone, base)

    #コンテキスト（会話履歴保存）
    ctx = USER_CONTEXT[user_id]
    ctx ["last_question"] = text
    ctx ["last_answer"] = response
    ctx ["last_label"] = None

    save_log(text, response)
    return response

#======
#フォールバックの選択肢部分
#======
def handle_choice(user_id: str, text: str, tone: str, normalize_question) -> str:
    #await_choiceの時のみ呼ばれる
    t = text.strip()

    if not t.isdigit():
        response = "番号でお答えください。(例:1)"
        save_log(text, response)
        return response
    
    idx = int(t) - 1
    cands = SESSION[user_id]["cands"]

    if not (0 <= idx < len(cands)):
        response = "番号でお答えください。(例:1)"
        save_log(text, response)
        return response
    
    chosen = cands[idx]
    user_input = normalize_question(chosen)

    best_match = None
    best_sim = 0.0
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT question, answer FROM faq")
        rows = cur.fetchall()
        for row in rows:
            q = row["question"] if USE_MYSQL else row[0]
            a = row["answer"] if USE_MYSQL else row[1]
            sim = Levenshtein.ratio(user_input, q)
            if sim > best_sim:
                best_sim = sim
                best_match = a
    finally:
        conn.close()
    
    SESSION[user_id]["await_choice"] = False
    SESSION[user_id]["cands"] = []

    response = best_match if (best_match and best_sim >= 0.6) else \
        "申し訳ありませんが、その質問には対応していません。\n後ほど担当者から返信いたします"

    save_log(text, response)
    return response

#======
#挨拶(greeting)部分
#======
def handle_greeting(user_id: str, text: str, tone: str) -> str:
    #挨拶文が含まれていたとき
    greetings = ["こんにちは", "おはようございます", "こんばんわ", "お疲れ様です", "お世話になります"]

    matched = None
    for g in greetings:
        if g in text:
            matched = g
            break
    
    if not matched:
        matched = "こんにちは"

    base_response = f"{matched}！いつもありがとうございます！"
    response = apply_style(tone, base_response, opener=False, closer=False)

    save_log(text, response)
    return response

#======
#FAQ検索部分
#======
def handle_faq(user_id: str, text: str, tone: str, normalize_question) -> str:
    user_input = normalize_question(text)
    #日付抽出用の正規表現（試合日・会場紐付け）
    m = re.search(r"\d{1,2}/\d{1,2}", text) 
    if m:
        date_str = m.group()   # "7/10"
        month, day = date_str.split("/") #月/日の形式にする
        year = "2026"
        db_date = f"{year}-{int(month):02d}-{int(day):02d}" #DB形式に変換する
        
        conn = get_db_connection()
        cur = conn.cursor()

        #日付検索（DB）
        try:
            if USE_MYSQL:
                cur.execute( #db_dateと同じ日付を検索（MYSQL版）
                    "SELECT stadium_name FROM map_response WHERE game_date = %s",
                    (db_date,)
                )
            else:
                cur.execute( #db_dateと同じ日付を検索（SQLite版）
                    "SELECT stadium_name FROM map_response WHERE game_date = ?",
                    (db_date,)
                )
            row = cur.fetchone() #ヒットしたらrowに入れる
        finally:
            conn.close()

        #日付がマッチした時(rowに値が入っている時)
        if row:
            if USE_MYSQL:
                stadium_name = row["stadium_name"]
            else:
                stadium_name = row[0]

            map_url = make_map_url(stadium_name)

            base = f"{date_str}の会場は{stadium_name}です。\n{map_url}"

            ctx = USER_CONTEXT[user_id]
            ctx["last_question"] = text
            ctx["last_answer"] = base
            ctx["last_label"] = None

            response = apply_style(tone, base)
            save_log(text, response)

            return response


    best_match = None
    best_sim = 0.0
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT question, answer, has_map FROM faq")
        rows = cur.fetchall()
        for row in rows:
            q = row["question"] if USE_MYSQL else row[0]
            a = row["answer"] if USE_MYSQL else row[1]
            m = row["has_map"] if USE_MYSQL else row[2]#追加

            q_norm = normalize_question(q)
            sim = Levenshtein.ratio(user_input, q_norm)
            if sim > best_sim:
                best_sim = sim
                best_match = {"q":q, "a":a, "m":m, "sim":sim}
    finally:
        conn.close()
    
    #ヒットした場合
    if best_match and best_sim >=0.6:
        base = best_match["a"]

        if best_match["m"] == 1: #Googlemap処理
            map_query = normalize_question(best_match["q"])
            map_url = make_map_url(map_query)
            base += "\n" + map_url

        ctx = USER_CONTEXT[user_id]
        ctx ["last_question"] = user_input
        ctx ["last_answer"] = base
        ctx ["last_label"] = None

        response = apply_style(tone, base)
        save_log(text, response)
        return response
    
    #フォールバック    
    cands = suggest_labels(text, SUGGEST_POOL)
    if cands:
        SESSION[user_id]["await_choice"] = True
        SESSION[user_id]["cands"] = cands
        response = make_choice_message(cands)
        save_log(text, response)
        return response
    
    base = "申し訳ありませんが、その質問には対応しておりません。\n後ほど担当者から返信いたします"
    ctx = USER_CONTEXT[user_id]
    ctx["last_question"] = user_input
    ctx["last_answer"] = base
    ctx["last_label"] = None

    response = apply_style(tone, base)
    save_log(text, response)
    return response