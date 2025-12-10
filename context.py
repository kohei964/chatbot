from collections import defaultdict
from difflib import SequenceMatcher
import re

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