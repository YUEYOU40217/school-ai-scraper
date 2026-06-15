import re

def clean_title(title):
    """去除標題中的前後空白與無效字元"""
    return title.strip()

def extract_date(text):
    """從文字中萃取日期，若無則回傳 None"""
    match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', text)
    if match:
        return match.group(1)
    return None

def is_valid_announcement(title, href):
    """過濾掉無效的導覽連結"""
    garbage_words = ["跳到", "首頁", "menu", "交通", "login", "english", "search", "void(0)"]
    if not href or len(title) < 5:
        return False
    if any(w in title.lower() for w in garbage_words):
        return False
    return True
