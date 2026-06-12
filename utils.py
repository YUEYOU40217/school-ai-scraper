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

def fetch_links(target_url, row_selector, link_selector):
    """抓取公告頁面連結、整行文字、網站名稱與日期"""
    try:
        resp = session.get(target_url, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 自動抓取網頁的 Title 當作來源名稱
        source_name = soup.title.get_text(strip=True) if soup.title else "未命名網頁"
        
        rows = soup.select(row_selector) if row_selector else [soup]
        links = []
        seen_urls = set()
        
        for row in rows:
            row_text = row.get_text(separator=' ', strip=True) 
            
            # 嘗試從整行文字中萃取日期（支援 2026-06-12 或 115-06-12 或 2026/06/12 等各式常見格式）
            date_match = re.search(r'(\d{3,4}[-/]\d{1,2}[-/]\d{1,2})', row_text)
            date_str = date_match.group(1) if date_match else "0000-00-00"
            
            a_tags = row.select(link_selector) if link_selector else row.find_all('a')
            for a_tag in a_tags:
                if a_tag and a_tag.get('href'):
                    title = a_tag.get_text(strip=True)
                    href = a_tag.get('href')
                    full_url = urljoin(target_url, href)
                    
                    if not title or len(title) < 4: continue
                    if full_url in seen_urls: continue
                    
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

def process_ai(title_text, template, client):
    """將 config 的提示詞模板帶入，並替換標題交由 AI 解析關鍵字"""
    prompt = template.replace("{title}", title_text)
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
        print(f"AI 解析錯誤: {e}")
        return {"keywords": ["解析失敗"]}
