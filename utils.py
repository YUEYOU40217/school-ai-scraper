import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import json
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
    """抓取公告頁面連結、整行文字並過濾雜訊"""
    try:
        resp = session.get(target_url, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        
        rows = soup.select(row_selector) if row_selector else [soup]
        links = []
        seen_urls = set()
        
        for row in rows:
            row_text = row.get_text(separator=' ', strip=True) 
            
            a_tags = row.select(link_selector) if link_selector else row.find_all('a')
            for a_tag in a_tags:
                if a_tag and a_tag.get('href'):
                    title = a_tag.get_text(strip=True)
                    href = a_tag.get('href')
                    full_url = urljoin(target_url, href)
                    
                    if not title or len(title) < 4: continue
                    if full_url in seen_urls: continue
                    
                    links.append({"title": title, "href": href, "row_text": row_text})
                    seen_urls.add(full_url)
        return links
    except Exception as e:
        print(f"抓取清單失敗: {e}")
        return []

def process_ai(title_text, template, client):
    """直接將 config 的提示詞帶入，並替換標題關鍵字"""
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
