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

def fetch_raw_html(target_url):
    """擁有三重突破保險的底層 HTML 抓取器"""
    resp_text = None
    scraper_api_key = os.environ.get("SCRAPER_API_KEY")
    
    if scraper_api_key:
        proxy_url = "https://api.scraperapi.com/"
        payload = {'api_key': scraper_api_key, 'url': target_url}
        try:
            resp = requests.get(proxy_url, params=payload, timeout=30)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding
                return resp.text
        except Exception:
            pass

    try:
        resp = session.get(target_url, timeout=15, verify=False)
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            resp = requests.get(target_url, headers=headers, timeout=15, verify=False)
            resp.encoding = resp.apparent_encoding
            return resp.text
        except Exception:
            try:
                context = ssl._create_unverified_context()
                req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
                with urllib.request.urlopen(req, context=context, timeout=15) as response:
                    raw_data = response.read()
                    try:
                        return raw_data.decode('utf-8')
                    except UnicodeDecodeError:
                        return raw_data.decode('big5', errors='ignore')
            except Exception:
                return None

def clean_soup_garbage(soup):
    """【黑科技】直接拔掉網頁的導航、頁尾、廣告與樣式，只留核心公告區"""
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.extract()
    return soup

def fetch_links_smart(target_url):
    """【完全體盲猜版】自動尋找網頁中帶有日期的公告連結，並回傳原始碼與解析清單"""
    html_text = fetch_raw_html(target_url)
    if not html_text:
        return "抓取失敗", [], None
        
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        source_name = soup.title.get_text(strip=True) if soup.title else "未命名網頁"
        soup = clean_soup_garbage(soup)
        
        links = []
        seen_urls = set()
        all_a_tags = soup.find_all('a')
        
        garbage_words = ["跳到", "主要內容", "previous", "next", "首頁", "返回", "coreui", "登入", "隱私權"]
        
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
                    
        return source_name, links, soup
    except Exception as e:
        print(f"抓取清單解析失敗: {e}")
        return "抓取失敗", [], None

def find_next_page_urls(soup, current_url, max_pages=3):
    """【AI級盲猜換頁】自動從網頁的頁碼按鈕中通靈出前 N 頁的完整網址"""
    discovered_urls = [current_url]
    if not soup or max_pages <= 1:
        return discovered_urls
        
    all_a_tags = soup.find_all('a')
    page_patterns = [
        r'page=\d+', r'p=\d+', r'-\d+\.php', r'index_\d+'
    ]
    
    # 尋找看起來像分頁的連結
    for a_tag in all_a_tags:
        href = a_tag.get('href', '')
        text = a_tag.get_text(strip=True)
        
        if not href or href.startswith('#') or href.startswith('javascript:'):
            continue
            
        full_url = urljoin(current_url, href)
        if full_url in discovered_urls:
            continue
            
        # 策略 1：如果文字本身就是數字 (例如 2, 3, 4) 且網址符合分頁特徵
        if text.isdigit() and int(text) <= max_pages:
            if any(re.search(pat, href.lower()) for pat in page_patterns):
                discovered_urls.append(full_url)
                
        # 策略 2：如果文字寫著 "下一頁" 或 "Next"
        elif any(w in text.lower() for w in ["下一頁", "next", "後一頁"]):
            discovered_urls.append(full_url)

    # 去重並依網址特徵做排序，確保順序大致符合 1 -> 2 -> 3
    unique_urls = list(dict.fromkeys(discovered_urls))
    return unique_urls[:max_pages]

def process_ai_batch(titles_list, template, client, allowed_years_str="2025, 2026"):
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
