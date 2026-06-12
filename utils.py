import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import json
from urllib.parse import urljoin

def get_robust_session():
    """建立帶有自動重試機制的 Session，提高連線穩定度"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

session = get_robust_session()

def fetch_links(target_url, row_selector, link_selector):
    """抓取公告頁面連結並過濾雜訊"""
    try:
        resp = session.get(target_url, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        
        rows = soup.select(row_selector) if row_selector else [soup]
        links = []
        seen_urls = set()
        
        for row in rows:
            a_tags = row.select(link_selector) if link_selector else row.find_all('a')
            for a_tag in a_tags:
                if a_tag and a_tag.get('href'):
                    title = a_tag.get_text(strip=True)
                    href = a_tag.get('href')
                    full_url = urljoin(target_url, href)
                    
                    if not title or len(title) < 4: continue
                    if full_url in seen_urls: continue
                    
                    links.append({"title": title, "href": href})
                    seen_urls.add(full_url)
        return links
    except Exception as e:
        print(f"❌ 抓取清單失敗: {e}")
        return []

def get_page_content(url):
    """安全開啟連結並抓取乾淨的網頁內文"""
    try:
        if any(x in url.lower() for x in ["javascript:", "flickr.com", ".pdf", ".docx", ".xlsx", ".zip", ".jpg", ".png"]): 
            return None
            
        resp = session.get(url, timeout=10, stream=True)
        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            return None
            
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        
        for script in soup(["script", "style", "nav", "footer", "iframe", "header"]): 
            script.extract()
            
        return soup.get_text(separator=' ', strip=True)[:2000]
    except Exception as e:
        print(f"⚠️ 無法讀取內頁內容 {url}: {e}")
        return None

def process_ai(url, template, client):
    """網頁內容擷取與 AI 摘要 (使用最新版 Google GenAI SDK)"""
    content = get_page_content(url)
    if not content: 
        return {"summary": "無法抓取內容，該連結可能為附件檔案或無效網頁。"}
    
    prompt = template.replace("{content}", content)
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',  # 👈 換成你推薦的最強輕量模型！
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"🤖 AI 解析錯誤: {e}")
        return {"summary": "AI 解析失敗或回傳格式異常。"}
