import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import urllib3  
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import json
import re
from urllib.parse import urljoin

# 強制關閉 SSL 警告文字
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_robust_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

session = get_robust_session()

def fetch_links_smart(target_url):
    """【無格式盲猜版】自動尋找網頁中帶有日期的公告連結"""
    resp_text = None
    
    # 💡 雙重保險連線機制
    try:
        # 第一彈：嘗試用常規強固型 Session 連線
        resp = session.get(target_url, timeout=15, verify=False)
        resp.encoding = resp.apparent_encoding
        resp_text = resp.text
    except Exception as e:
        print(f"⚠️ [第一彈 Session 連線失敗] 錯誤原因: {e}，正在切換成獨立強行突破模式...")
        try:
            # 第二彈：如果 Session 被本地憑證卡死，直接脫離 Session，用全新乾淨的 requests 裸連
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            resp = requests.get(target_url, headers=headers, timeout=15, verify=False)
            resp.encoding = resp.apparent_encoding
            resp_text = resp.text
        except Exception as e2:
            print(f"❌ [雙重保險皆失敗] 無法連線至該網站: {e2}")
            return "抓取失敗", []

    try:
        soup = BeautifulSoup(resp_text, "html.parser")
        source_name = soup.title.get_text(strip=True) if soup.title else "未命名網頁"
        links = []
        seen_urls = set()
        all_a_tags = soup.find_all('a')
        
        garbage_words = ["跳到", "主要內容", "previous", "next", "首頁", "返回", "coreui"]
        
        for a_tag in all_a_tags:
            href = a_tag.get('href')
            title = a_tag.get_text(strip=True)
            
            if not href or not title or len(title) < 5: 
                continue
                
            if href.startswith('#') or any(w in title.lower() for w in garbage_words):
                continue
                
            full_url = urljoin(target_url, href)
            if full_url in seen_urls: 
                continue
                
            parent = a_tag.parent
            row_text = ""
            date_str = "0000-00-00"
            
            for _ in range(3):
                if parent:
                    row_text = parent.get_text(separator=' ', strip=True)
                    date_match = re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})', row_text)
                    if date_match:
                        date_str = date_match.group(1)
                        break
                    parent = parent.parent
            
            if date_str == "0000-00-00":
                continue
                
            links.append({
                "title": title, 
                "href": href, 
                "row_text": row_text,
                "date": date_str
            })
            seen_urls.add(full_url)
                    
        return source_name, links
    except Exception as e:
        print(f"抓取清單解析失敗: {e}")
        return "抓取失敗", []

def process_ai_batch(titles_list, template, client):
    prompt = template.replace("{batch_input}", "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles_list)]))
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"AI 批次解析錯誤: {e}")
        return [{"keywords": ["解析失敗"]} for _ in titles_list]
