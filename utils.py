import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import json
import re
from urllib.parse import urljoin

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
    try:
        resp = session.get(target_url, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        
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
        print(f"抓取清單失敗: {e}")
        return "抓取失敗", []

def process_ai_batch(titles_list, template, client):
    """【批次 AI 處理引擎】一次打包多個標題送給 AI，極大化節省 API 呼叫次數"""
    # 將標題清單轉化為帶有編號的文字串
    formatted_inputs = "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles_list)])
    prompt = template.replace("{batch_input}", formatted_inputs)
    
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
        # 發生錯誤時，回傳與輸入數量相符的保底失敗防護
        return [{"keywords": ["解析失敗"]} for _ in titles_list]
