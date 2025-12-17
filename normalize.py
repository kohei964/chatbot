import re
import unicodedata

_PUNCT_RE = re.compile(r"[！？!?｡。．.,、…‥ー〜～]+")
_SPACE_RE = re.compile(r"\s+")
_TAIL_RE = re.compile(r"(です|ます|でした|ました|でしょう|だよ|だね|かな|かも)?(か)?$")

def normalize_input(text: str) -> str:
    t = text.strip()

    #数字のみはそのまま
    if re.fullmatch(r"\d+", t):
        return t
    
    t = unicodedata.normalize("NFKC", t) #半角・全角の表記統一
    t = _SPACE_RE.sub(" ", t) #連続する空白・タブをまとめる
    t = _PUNCT_RE.sub("?", t) #記号(!?など)を統一
    t = _TAIL_RE.sub("", t) #文末の丁寧語を削る

    return t.strip()