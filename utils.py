import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import urllib3  
import urllib.request
import ssl             
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import json
import re
import os
from urllib.parse import urljoin

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
    """【單頁全抓版】破防連線並撈取網頁中所有帶有日期的公告連結"""
    resp_text = None
    scraper_api_key = os.environ.get("SCRAPER_API_KEY")
    
    if scraper_api_key:
        print(f"[跳板模式] 正在透過 Scraper API 連線: {target_url}")
        proxy_url = "[https://api.scraperapi.com/](https://api.scraperapi.com/)"
        payload = {'api_key': scraper_api_key, 'url': target_url}
        try:
            resp = requests.get(proxy_url, params=payload, timeout=30)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding
                resp_text = resp.text
        except Exception:
            pass

    if not resp_text:
        try:
            resp = session.get(target_url, timeout=15, verify=False)
            resp.encoding = resp.apparent_encoding
            resp_text = resp.text
        except Exception as e:
            print(f" [第一彈連線失敗] 原因: {e}，切換獨立模式...")
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                resp = requests.get(target_url, headers=headers, timeout=15, verify=False)
                resp.encoding = resp.apparent_encoding
                resp_text = resp.text
            except Exception as e2:
                print(f"[第二彈連線失敗] 原因: {e2}，切換終極 urllib...")
                try:
                    context = ssl._create_unverified_context()
                    req = urllib.request.Request(
                        target_url, 
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                    )
                    with urllib.request.urlopen(req, context=context, timeout=15) as response:
                        raw_data = response.read()
                        try:
                            resp_text = raw_data.decode('utf-8')
                        except UnicodeDecodeError:
                            resp_text = raw_data.decode('big5', errors='ignore')
                    print("[終極第三彈] 成功強行突破限制！")
                except Exception as e3:
                    print(f"[三重保險皆失敗] 無法連線: {e3}")
                    return "抓取失敗", []

    try:
        soup = BeautifulSoup(resp_text, "html.parser")
        source_name = soup.title.get_text(strip=True) if soup.title else "未命名網頁"
        
        # 移除沒用的網頁元件雜訊
        for el in soup(["script", "style", "nav", "footer", "header"]):
            el.extract()
            
        links = []
        seen_urls = set()
        all_a_tags = soup.find_all('a')
        
        garbage_words = ["跳到", "主要內容", "previous", "next", "首頁", "返回", "coreui", "登入"]
        
        for a_tag in all_a_tags:
            href = a_tag.get('href')
            title = a_tag.get_text(strip=True)
            
            if not href or not title or len(title) < 5: 
                continue
                
            if href.startswith('#') or href.startswith('javascript:') or any(w in title.lower() for w in garbage_words):
                continue
                
            full_url = urljoin(target_url, href)
            if full_url in seen_urls: 
                continue
                
            parent = a_tag.parent
            row_text = ""
            date_str = "0000-00-00"
            
            # 向上查找 3 層找日期
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
                "title": title.strip(), 
                "href": href, 
                "row_text": row_text,
                "date": date_str
            })
            seen_urls.add(full_url)
                    
        return source_name, links
    except Exception as e:
        print(f"解析失敗: {e}")
        return "抓取失敗", []

def process_ai_batch(titles_list, template, client, allowed_years_str):
    prompt = template.replace("{allowed_years}", allowed_years_str)
    prompt = prompt.replace("{batch_input}", "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles_list)]))
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        raw_text = response.text.strip()
        start_idx = raw_text.find('[')
        end_idx = raw_text.rfind(']')
        
        if start_idx != -1 and end_idx != -1:
            clean_json_str = raw_text[start_idx:end_idx + 1]
            return json.loads(clean_json_str)
        else:
            return json.loads(raw_text)
            
    except Exception as e:
        print(f"AI 批次解析錯誤: {e}")
        return [{"is_valid": False, "keywords": ["解析失敗"]} for _ in titles_list]
