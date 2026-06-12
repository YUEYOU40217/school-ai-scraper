import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
from urllib.parse import urljoin

def find_announcement_page(home_url):
    """功能一：自動導航，在首頁尋找疑似公告頁面的連結"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(home_url, timeout=15, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 關鍵字清單，你可以隨意新增
        keywords = ["公告", "最新消息", "NEWS", "資訊", "校園消息"]
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            if any(k in text for k in keywords):
                full_url = urljoin(home_url, a['href'])
                print(f"自動導航：發現疑似公告頁面 -> {text} ({full_url})")
                return full_url
        return home_url
    except Exception as e:
        print(f"導航失敗: {e}")
        return home_url

def fetch_links(target_url, row_selector):
    """功能二：抓取公告頁面連結並過濾雜訊"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(target_url, timeout=15, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.find_all(row_selector) or soup.find_all('a')
        
        links = []
        for row in rows:
            a_tag = row if row.name == 'a' else row.find('a')
            if a_tag and a_tag.get('href'):
                title = a_tag.get_text(strip=True)
                href = a_tag.get('href')
                # 過濾無意義連結
                if not title or len(title) < 4: continue
                if any(x in title for x in ["首頁", "English", "Search", "跳到", "登入"]): continue
                links.append({"title": title, "href": href})
        return links
    except Exception as e:
        print(f"抓取連結失敗: {e}")
        return []

def process_ai(content, template, model):
    """功能三：呼叫 AI 進行摘要"""
    prompt = template.format(content=content)
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return {"summary": "處理失敗，請點連結查看。"}
