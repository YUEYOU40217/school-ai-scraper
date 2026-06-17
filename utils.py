import requests
import re
import urllib3

# 關閉 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_page_html(url):
    """最穩定的網頁原始 HTML 抓取"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = response.apparent_encoding
        return response.text
    except Exception as e:
        print(f"連線異常 ({url}): {e}")
        return None

def clean_pure_text(text):
    """僅清理空白與換行，保留完整原始文字"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def match_date_format(text):
    """精準匹配 YYYY-MM-DD 或 YYYY/MM/DD 格式"""
    match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', text)
    if match:
        return match.group(1)
    return None
