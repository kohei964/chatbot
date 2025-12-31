#======================
# どのルートに行くかの分岐
# =====================

import re

_GREETINGS = ("こんにちは", "おはよう", "こんばんは", "こんばんわ", "お疲れ様", "お世話になります")

_REPEAT_RE = re.compile(
    r"(さっき|前の|先ほど|さきほど).*(もう一度|もういちど|もっかい|教えて|おしえて)"
    r"|もう一度(教えて)?"
    r"|さっきの(回答|やつ)?(もう一回|もう一度)"
)

def detect_intent(user_id: str, text: str, *, lang: str, session) -> str:
    """
    intent種類
    repeat / choice / non_ja / greeting / faq
    """

    t = text.strip()

    # 1)フォールバックの番号(choice)
    if session and session[user_id].get("await_choice") and t.isdigit():
        return "choice"
    
    # 2)繰り返し(repeat)
    if _REPEAT_RE.search(t):
        return "repeat"
    
    # 3)日本語か英語か(non_ja)
    if lang == "en":
        return "non_ja"
    
    # 4)挨拶(greeting)
    if any(g in t for g in _GREETINGS):
        return "greeting"
    
    # 5)通常
    return "faq"


