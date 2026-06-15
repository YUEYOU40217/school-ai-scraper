import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import urllib3  
import urllib.request
import ssl             
import json
import os
from google.genai import types

# 關閉常規的憑證警告文字
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_robust_session():
    """建立帶有重試機制的穩定 requests Session"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

session = get_robust_session()

def fetch_html_text(target_url):
    """三層防線取得網頁 HTML 原始碼"""
    resp_text = None
    scraper_api_key = os.environ.get("SCRAPER_API_KEY")
    
    # 優先防線：使用 Scraper API 代理連線
    if scraper_api_key:
        print(f"[跳板模式] 正在連線至: {target_url}")
        proxy_url = "https://api.scraperapi.com/"
        try:
            resp = requests.get(proxy_url, params={'api_key': scraper_api_key, 'url': target_url}, timeout=30)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding
                print("[跳板模式] 成功取得網頁原始碼。")
                return resp.text
        except Exception as e:
            print(f"[跳板模式異常] 切換回原有機制... ({e})")

    # 第一彈：常規 Session 連線
    try:
        resp = session.get(target_url, timeout=15, verify=False)
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception as e:
        print(f"[第一彈連線失敗] 切換獨立模式... ({e})")

    # 第二彈：獨立 requests 連線
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(target_url, headers=headers, timeout=15, verify=False)
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception as e2:
        print(f"[第二彈連線失敗] 啟動終極第三彈... ({e2})")

    # 第三彈：urllib 強行突破
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=context, timeout=15) as response:
            raw_data = response.read()
            try:
                return raw_data.decode('utf-8')
            except UnicodeDecodeError:
                return raw_data.decode('big5', errors='ignore')
    except Exception as e3:
        print(f"[三重保險皆失敗] 無法取得網頁: {e3}")
        return None

def process_ai_batch(titles_list, template, client):
    """將公告標題分批送交給 Gemini 進行關鍵字萃取"""
    if not titles_list:
        return []
        
    prompt = template.replace("{batch_input}", "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles_list)]))
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        raw_text = response.text.strip()
        start_idx = raw_text.find('[')
        end_idx = raw_text.rfind(']')
        
        if start_idx != -1 and end_idx != -1:
            return json.loads(raw_text[start_idx:end_idx + 1])
        return json.loads(raw_text)
            
    except Exception as e:
        print(f"AI 解析錯誤: {e}")
        return [{"keywords": ["解析失敗"]} for _ in titles_list]
