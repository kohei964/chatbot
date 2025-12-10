
from collections import defaultdict
from difflib import SequenceMatcher
import Levenshtein
import re
import random

from db import get_db_connection, USE_MYSQL

#=== 感情分析↓↓ ========================
#汚い言葉検地用の変数
INSULT_WORDS = [
    "死ね", "しね", "バカ", "ばか", "アホ", "クズ", "ゴミ",
    "きもい", "キモい", "うざい", "うぜえ", "カス",
    "黙れ", "だまれ", "消えろ", "クソ", "ふざけるな", "ふざけんな",
]

#リアクション検知用
ANGRY_WORDS = [
    r"なんだよ",
    r"意味わからん",
    r"使えね[えぇ]?",
    r"最悪",
]

#ユーザーの発言からの判定("normal"|"angry"|"insult")用の関数
def detect_tone(text: str) -> str:
    t = text.strip()

    #汚い言葉検知
    for w in INSULT_WORDS:
        if w in t:
            return "insult"
    
    #リアクション検知
    for pattern in ANGRY_WORDS:
        if re.search(pattern, t):
            return "angry"
    
    return "normal"

#丁寧レス用の関数
def reply_for_angry(tone: str, core_reply: str) -> str:
    #tone ("normal"|"angry"|"insult")

    if tone == "insult":
        prefix = (
            "ご不快な思いをさせてしまい申し訳ありません。内容を一部控えめにご案内いたします。\n"
            "大変申し訳ありませんが、丁寧な言葉でお問い合わせいただけると助かります"
        )
    elif tone == "angry":
        prefix = (
            "ご不便をおかけしているようで申し訳ありません。\n"
            "状況を整理しながら、できる限り丁寧にご案内いたします。\n"
        )
    else:
        #通常トーン(そのまま返す)
        return core_reply
    
    return f"{prefix}\n{core_reply}"
#=== 感情分析↑↑ ========================

#=== 言語判定（英語/日本語)↓↓ ============
def detect_language(text: str) -> str:
    """
    言語判定
        "ja"    : 日本語のみ（ひらがな、カタカナ、漢字） 
        "en"    : 英語のみ
        "mixed" : 日本語+英語ミックス
        "other" : どちらもほぼなし（絵文字、記号のみ等）
    """
    t = text.strip() #空白・改行などを削除

    #ひらがな/カタカナ/漢字
    has_ja = bool(re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', t)) 
    #英字
    has_en = bool(re.search(r'[A-Za-z]', t))

    if has_ja and not has_en:
        return "ja"
    elif has_en and not has_ja:
        return "en"
    elif has_ja and has_en:
        return "mixed"
    else:
        return "other"
#=== 言語判定（英語/日本語)↑↑ ============

#=== 自然言語↓↓ ======================== 
#冒頭につける変数（random）
OPENERS = [
    "お問い合わせありがとうございます。",
    "ご質問ありがとうございます。",
    "メッセージありがとうございます。",
    "ご連絡いただきありがとうございます。",
]

#締めくくりにつける変数(random)
CLOSERS = [
    "その他気になる点がございましたら、遠慮なくお知らせください。",
    "もし追加でご不明な点があれば、お気軽にご質問ください。",
    "引き続きどうぞよろしくお願いいたします。",
    "お役に立てれば幸いです。",
]

#自然言語用の関数
def natural_text(core_reply: str, use_opener: bool = True, use_closer: bool = True) -> str:
    parts = []

    if use_opener:
        parts.append(random.choice(OPENERS))
    
    parts.append(core_reply.strip())

    if use_closer:
        parts.append(random.choice(CLOSERS))
    
    return "\n".join(parts)
#=== 自然言語↑↑ ==========================

#=== コンテキスト（会話履歴保持）↓↓ ==========
USER_CONTEXT = defaultdict(lambda: {
    "last_question": None,
    "last_answer": None,
    "last_label": None, #キーワード（営業時間、試合会場...）
})

#リピート要求(振り返り)を検知する変数
REPEAT_WORDS = [
    r"(さっき|前の|先ほど|さきほど).*(もう一度|もういちど|教えて|おしえて)",
    r"もう一度(教えて)?",
    r"さっきの(回答|やつ)?(もう一回|もう一度)",
]

#↑の関数
def repeat_request(text: str) -> bool:
    t = text.strip()
    for pat in REPEAT_WORDS:
        if re.search(pat, t):
            return True
    return False

#=== コンテキスト（会話履歴保持）↑↑ ==========

#=== フォールバック部分↓↓ ===================
#フォールバック用セッション管理
SESSION = defaultdict(lambda: {"await_choice": False, "cands":[]})

SUGGEST_POOL = ["営業時間","試合会場","駐車場","選手登録期限","試合日程","雨天時の対応","エントリー","試合球の規定","緊急連絡先"]  # 追加

def suggest_labels(user_text, pool, topn=3):
    scored = []
    for label in pool:
        s = SequenceMatcher(None, user_text, label).ratio()
        scored.append((s, label))
    scored.sort(reverse=True)
    return [lab for _, lab in scored[:topn]]

def make_choice_message(cands):
    bullets = "\n".join([f"・{i+1}. {lab}" for i, lab in enumerate(cands)])
    return (
        "すみません、よくわかりませんでした。次のどれが近いですか？\n"
        f"{bullets}\n番号でお答えください。"
    )
#=== フォールバック部分↑↑ ===================

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