import random

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
