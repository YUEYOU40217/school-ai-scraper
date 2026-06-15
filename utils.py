import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import urllib3
import urllib.request
import ssl
import json
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_robust_session():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def fetch_html_text(target_url):
    # 嘗試用 requests 抓取，失敗後 fallback 使用 urllib
    try:
        session = get_robust_session()
        resp = session.get(target_url, timeout=20, verify=False)
        resp.encoding = resp.apparent_encoding
        return resp.text
    except:
        try:
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'}), context=context, timeout=20) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"連線失敗: {e}")
            return None
