import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import urllib3
import urllib.request
import ssl

# 關閉 SSL 驗證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_robust_session():
    """建立穩定的 requests Session"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    # 設定重試機制
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def fetch_html_text(target_url):
    """嘗試三種連線方式確保取得網頁內容"""
    # 方式一：requests Session
    try:
        session = get_robust_session()
        resp = session.get(target_url, timeout=20, verify=False)
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception as e:
        print(f"[連線失敗] 嘗試方式二: {e}")
        
    # 方式二：urllib 底層連線 (針對較嚴格的伺服器)
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=context, timeout=20) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[終極連線失敗]: {e}")
        return None
