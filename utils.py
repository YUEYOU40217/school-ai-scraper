import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup
import google.generativeai as genai
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

# 全域連線池
session = get_robust_session()

def find_announcement_page(home_url):
    """自動導航：在首頁尋找疑似公告頁面的連結"""
    try:
        resp = session.get(home_url, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        
        keywords = ["公告", "最新消息", "NEWS", "資訊", "校園消息", "最新公告"]
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            if any(k in text for k in keywords):
                full_url = urljoin(home_url, a['href'])
                print(f"🌟 自動導航：發現疑似公告頁面 -> {text} ({full_url})")
                return full_url
        return home_url
    except Exception as e:
        print(f"❌ 導航失敗: {e}")
        return home_url

def fetch_links(target_url, row_selector, link_selector):
    """抓取公告頁面連結並過濾雜訊、防止重複抓取"""
    try:
        resp = session.get(target_url, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 根據 config 的 row_selector 切分區塊（例如 tr）
        rows = soup.select(row_selector) if row_selector else [soup]
        
        links = []
        seen_urls = set() # 用於網址去重
        
        for row in rows:
            # 在該區塊內尋找符合 link_selector 的標籤
            a_tags = row.select(link_selector) if link_selector else row.find_all('a')
            
            for a_tag in a_tags:
                if a_tag and a_tag.get('href'):
                    title = a_tag.get_text(strip=True)
                    href = a_tag.get('href')
                    full_url = urljoin(target_url, href)
                    
                    # 基礎雜訊過濾
                    if not title or len(title) < 4: continue
                    if any(x in title for x in ["首頁", "English", "Search", "跳到", "登入", "網站地圖", "回頁首", "下一頁", "上一頁"]): continue
                    if full_url in seen_urls: continue # 抓過就跳過
                    
                    links.append({"title": title, "href": href})
                    seen_urls.add(full_url)
                    
        return links
    except Exception as e:
        print(f"❌ 抓取清單失敗: {e}")
        return []

def get_page_content(url):
    """安全開啟連結並抓取乾淨的網頁內文"""
    try:
        # 排除明顯的非網頁格式
        if any(x in url.lower() for x in ["javascript:", "flickr.com", ".pdf", ".docx", ".xlsx", ".zip", ".jpg", ".png"]): 
            return None
            
        # 使用 stream=True 先行檢查 Header，避免下載大型檔案導致當機
        resp = session.get(url, timeout=10, stream=True)
        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            return None
            
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 拔除無關網頁元件
        for script in soup(["script", "style", "nav", "footer", "iframe", "header"]): 
            script.extract()
            
        return soup.get_text(separator=' ', strip=True)[:2000] # 限制內文長度
    except Exception as e:
        print(f"⚠️ 無法讀取內頁內容 {url}: {e}")
        return None

def process_ai(url, template, model):
    """網頁內容擷取與 AI 摘要 (強制 JSON 模式)"""
    content = get_page_content(url)
    if not content: 
        return {"summary": "無法抓取內容，該連結可能為附件檔案或無效網頁。"}
    
    prompt = template.replace("{content}", content)
    try:
        # 強制 Gemini 輸出符合 config 規範的標準 JSON
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"🤖 AI 解析錯誤: {e}")
        return {"summary": "AI 解析失敗或回傳格式異常。"}
