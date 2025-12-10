import Levenshtein

from db import get_db_connection, USE_MYSQL

from analysis import detect_tone, detect_language, reply_for_angry
from textgen import natural_text
from context import (
    USER_CONTEXT,
    SESSION,
    repeat_request,
    SUGGEST_POOL,
    suggest_labels,
    make_choice_message,
)

#=== ロジック部分↓↓ ========================
#類似語変換用のシノニム辞書を定義
SYNONYMS = {
    "営業時間": ["何時から", "何時まで", "受付時間", "営業", "オープン", "クローズ"],
    "試合会場": ["会場", "球場", "グラウンド", "住所", "アクセス", "地図", "最寄駅"],
    "駐車場": ["駐車", "パーキング", "車", "台数", "駐車料金", "満車", "混雑"],
    "選手登録期限": ["選手登録", "登録表", "提出期限", "締切", "いつまで"],
    "試合日程": ["日程", "スケジュール", "カレンダー", "予定", "試合いつ"],
    "雨天時の対応": ["雨", "雨天", "中止", "荒天", "天候", "開催可否"],
    "エントリー": ["参加申し込み", "申込", "エントリーフォーム", "申請"],
    "試合球の規定": ["試合球", "ボール", "球種", "何号", "ボール規定"],
    "緊急連絡先": ["緊急連絡", "連絡先", "電話番号", "連絡方法"],
}

#シノニムを正規化する関数（質問を変換）
def normalize_question(text):
    for key, synonyms in SYNONYMS.items():
        for synonym in synonyms:
            if synonym in text:
                return key #正規化されたキーワードを返す
    return text #該当なしならそのまま


#=========== 
# 応答部分
#===========
def get_response(user_id, text):

    tone = detect_tone(text) #感情分析用
    lang = detect_language(text) #言語判定（日本語/英語）

    #------------
    #"パターンA" 
    # 繰り返し判定ヒットした場合（repeat_request = True）の応答部分
    #------------
    if repeat_request(text):
        ctx = USER_CONTEXT[user_id] #ctx = コンテキスト

        #前回の会話履歴が保存されているかの確認
        if ctx["last_answer"]: #コンテキストが残っているパターン
            base_response = ctx["last_answer"]

            #感情表現 + 自然言語も
            if tone in ("angry", "insult"):
                core = reply_for_angry(tone, base_response)
                response = natural_text(core, use_opener=False, use_closer=True)
            else:
                response = natural_text(base_response)
            
            #ログ保存
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
            return response
        else: #初回など、履歴(last_answer)が空の場合
            response = "直前の会話がありません。お手数ですが、もう一度質問してください"
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
            return response

    

    #------------
    #"パターンB" 
    # 通常の応答部分
    #------------
    #⓪日本語以外だった時の処理
    if lang in ("en"):
        base_response = (
            "恐れ入りますが、\n日本語でのお問い合わせをお願いいたします。"
        )

        if tone in ("angry", "insult"):
            core = reply_for_angry(tone, base_response)
            response = natural_text(core, use_opener=False, use_closer=True)
        else:
            response = natural_text(base_response)

        # コンテキスト更新
        ctx = USER_CONTEXT[user_id]
        ctx["last_question"] = text
        ctx["last_answer"]   = response
        ctx["last_label"]    = None

        # ログ保存
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

        return response
    
    # ①番号待ちの処理
    if SESSION[user_id]["await_choice"]:
        normalized = text.strip()
        if normalized.isdigit():
            idx = int(normalized) - 1
            cands = SESSION[user_id]["cands"]
            if 0 <= idx < len(cands):
                #選ばれた候補を再検索
                chosen = cands[idx]
                user_input = normalize_question(chosen)
                
                conn = get_db_connection()
                cursor = conn.cursor()
                best_match = None
                highest_similarity = 0.0

                #ログ保存
                try:
                    cursor.execute("SELECT question, answer FROM faq")
                    results = cursor.fetchall()
                    for row in results:
                        db_question = row["question"] if USE_MYSQL else row[0]
                        db_answer   = row["answer"]   if USE_MYSQL else row[1]
                        sim = Levenshtein.ratio(user_input, db_question)
                        if sim > highest_similarity:
                            highest_similarity = sim
                            best_match = db_answer
                except Exception as e:
                    print(f"Error: {e}")
                finally:
                    conn.close()
                
                # 番号処理終わり
                SESSION[user_id]["await_choice"] = False
                SESSION[user_id]["cands"] = []
                
                response = best_match if(best_match and highest_similarity >= 0.6) \
                           else "申し訳ありませんが、その質問には対応しておりません。\n後ほど担当者から返信いたします"
                
                #ログ保存
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

                return response
            
        # 数字以外や範囲外
        return "番号でお答えください。（例：1）"


    # --- ② 通常フロー：挨拶処理 ---
    greetings = ["こんにちは", "おはようございます", "こんばんわ", "お疲れ様です", "お世話になります"]
    for greeting in greetings:
        if greeting in text:
            base_response = f"{greeting}！いつもありがとうございます。"

            #感情分析+自然言語組み合わせ
            if tone in ("angry", "insult"):
                #荒れている時用（丁寧モード+クロージングだけ自然言語化）
                core = reply_for_angry(tone, base_response)
                response = natural_text(core, use_opener=False, use_closer=True)
            else:
                #通常時用（冒頭、クロージングともに自然言語化）
                response = natural_text(base_response, use_opener=False, use_closer=False)
            
            #ログ保存
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
                print(f"ログ保存エラー:{e}" )
            finally:
                conn.close()
            return response

    # --- ③ シノニム正規化 → FAQ検索 ---
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
            db_question = row["question"] if USE_MYSQL else row[0]
            db_answer   = row["answer"]   if USE_MYSQL else row[1]
            similarity = Levenshtein.ratio(user_input, db_question)
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = db_answer
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

    # --- ④ 応答決定：ヒット or フォールバック候補提示 ---
    #ヒットした場合
    if highest_similarity >= 0.6 and best_match:
        base_response = best_match

        #今回の回答をコンテキスト（履歴）に記録
        USER_CONTEXT[user_id]["last_question"] = user_input
        USER_CONTEXT[user_id]["last_answer"] = base_response

        #感情分析+自然言語組み合わせ
        if tone in ("angry", "insult"):
            #荒れている時（丁寧モード + クロージングのみ自然言語化 ）
            core = reply_for_angry(tone, base_response)
            response = natural_text(core, use_opener=False, use_closer=True)
        else:
            #通常時用（冒頭 + クロージングどちらも自然言語化)
            response = natural_text(base_response)

    #ヒットしなかった場合（フォールバック）
    else:
        # 候補プール（SUGGEST_POOLから）
        pool = SUGGEST_POOL
        cands = suggest_labels(text, pool)
        if cands:
            SESSION[user_id]["await_choice"] = True
            SESSION[user_id]["cands"] = cands
            response = make_choice_message(cands)
        #自然言語化
        else:
            base_response = "申し訳ありませんが、その質問には対応しておりません。\n後ほど担当者から返信いたします"

            #今回の回答をコンテキスト（履歴）に記録
            USER_CONTEXT[user_id]["last_question"] = user_input
            USER_CONTEXT[user_id]["last_answer"] = base_response

            if tone in ("angry", "insult"):
                ##荒れている時（prefix + 回答 + クロージングのみ自然言語化 ）
                core = reply_for_angry(tone, base_response)
                response = natural_text(core, use_opener=False, use_closer=True)
            else:
                #通常時用
                response = natural_text(base_response)

    # --- ⑤ 共通ログ保存（DBにINSERT） ---
    try:
        conn = get_db_connection() #DB接続
        cursor = conn.cursor()
        insert_log_query = ( #MySQLとSQLiteで分ける処理
            "INSERT INTO chat_logs (user_message, bot_response) VALUES (%s, %s)"
            if USE_MYSQL else
            "INSERT INTO chat_logs (user_message, bot_response) VALUES (?, ?)"
        )
        cursor.execute(insert_log_query, (text, response)) #ユーザー側：text, Bot側：response 
        conn.commit() #永続化
    except Exception as e: #エラーハンドリング
        print(f"ログ保存エラー: {e}")
    finally:
        conn.close()

    return response
#=== ロジック部分↑↑ ===============================