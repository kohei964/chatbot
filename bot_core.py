from intent import detect_intent
from handlers import (
    handle_choice,
    handle_repeat,
    handle_non_ja,
    handle_greeting,
    handle_faq,
)
from analysis import detect_tone, detect_language
from context import (
    SESSION,
)
from normalize import normalize_input

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
# handlersへの指示
#===========
def get_response(user_id, text):
    text = normalize_input(text)
    tone = detect_tone(text)
    lang = detect_language(text)
    intent = detect_intent(user_id, text, session=SESSION, lang=lang)

    if intent == "repeat":
        return handle_repeat(user_id, text, tone)
    
    if intent == "choice":
        return handle_choice(user_id, text, tone, normalize_question)
    
    if intent == "non_ja":
        return handle_non_ja(user_id, text, tone)

    if intent == "greeting":
        return handle_greeting(user_id, text, tone)
    
    #faqに繋げる
    return handle_faq(user_id, text, tone, normalize_question)
        

#=== ロジック部分↑↑ ===============================