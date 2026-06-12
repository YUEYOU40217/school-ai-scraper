import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json

def fetch_links(base_url, row_selector):
    """功能一：抓取網頁上所有的潛在連結"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(base_url, timeout=15, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.find_all(row_selector) or soup.find_all('a')
        
        links = []
        for row in rows:
            a_tag = row if row.name == 'a' else row.find('a')
            if a_tag and a_tag.get('href'):
                links.append({"title": a_tag.get_text(strip=True), "href": a_tag.get('href')})
        return links
    except Exception as e:
        print(f"抓取連結失敗: {e}")
        return []

def process_ai(content, template, model):
    """功能二：呼叫 AI 整理摘要"""
    prompt = template.format(content=content)
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return {"summary": "處理失敗，請點連結查看。"}
