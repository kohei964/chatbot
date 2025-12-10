import re

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