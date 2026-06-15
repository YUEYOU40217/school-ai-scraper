import os
import re
import json
import ssl
import urllib.request
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import urllib3
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# 關閉不安全連線的 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_robust_session():
    """建立具備自動重試機制的強固型 Session"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

session = get_robust_session()

def fetch_html_robust(target_url):
    """強固型網頁原始碼抓取核心（整合 ScraperAPI 與三重後援防線）"""
    scraper_api_key = os.environ.get("SCRAPER_API_KEY")
    
    if scraper_api_key:
        proxy_url = "https://api.scraperapi.com/"
        payload = {'api_key': scraper_api_key, 'url': target_url}
        try:
            resp = requests.get(proxy_url, params=payload, timeout=30)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding
                return resp.text
        except Exception as e:
            print(f"[跳板模式異常] {target_url} 嘗試切換回原有機制... 錯誤: {e}")

    try:
        resp = session.get(target_url, timeout=15, verify=False)
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception as e:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            resp = requests.get(target_url, headers=headers, timeout=15, verify=False)
            resp.encoding = resp.apparent_encoding
            return resp.text
        except Exception as e2:
            try:
                context = ssl._create_unverified_context()
                req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, context=context, timeout=15) as response:
                    raw_data = response.read()
                    try:
                        return raw_data.decode('utf-8')
                    except UnicodeDecodeError:
                        return raw_data.decode('big5', errors='ignore')
            except Exception as e3:
                print(f"[所有連線管道皆失敗] 無法連線至: {target_url}")
                return None

def fetch_links_smart(target_url):
    """【第一層】無差別全量掃描網頁，抓取列表頁上「所有」連結與周邊文字"""
    resp_text = fetch_html_robust(target_url)
    if not resp_text:
        return "抓取失敗", []

    try:
        soup = BeautifulSoup(resp_text, "html.parser")
        source_name = soup.title.get_text(strip=True) if soup.title else "未命名網頁"
        links = []
        seen_urls = set()
        all_a_tags = soup.find_all('a')
        
        for a_tag in all_a_tags:
            href = a_tag.get('href')
            title = a_tag.get_text(strip=True)
            
            # 排除無效點擊
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
                
            full_url = urljoin(target_url, href)
            if full_url in seen_urls: 
                continue
                
            # 抓取該連結「上下三層父節點」內的所有文字
            parent = a_tag.parent
            row_text = ""
            for _ in range(3):
                if parent:
                    row_text = parent.get_text(separator=' ', strip=True)
                    if len(row_text) > len(title):
                        break
                    parent = parent.parent
            
            display_title = title if title else (row_text[:30] if row_text else "未命名連結")
            
            links.append({
                "title": display_title, 
                "href": full_url, 
                "list_context": row_text if row_text else display_title
            })
            seen_urls.add(full_url)
                    
        print(f"[全量清單掃描成功] 共撈到 {len(links)} 個連結，即將進行無差別深度抓取。")
        return source_name, links
    except Exception as e:
        print(f"抓取清單解析失敗: {e}")
        return "抓取失敗", []

def fetch_detail_content(url):
    """【第二層】深入公告內頁，一分不差抓取全部純文字內容"""
    if any(url.lower().endswith(ext) for ext in ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.odt', '.zip', '.rar']):
        return f"[此為附件檔案，請參閱連結] {url}"

    html = fetch_html_robust(url)
    if not html:
        return "[內頁網頁讀取失敗]"
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        for element in soup(["script", "style"]):
            element.extract()
        
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        
        return text if text else "[此網頁無文字內容]"
    except Exception as e:
        return f"[內頁文字解析異常]: {e}"

def process_ai_batch(batch_data, template, client):
    """將包含 uuid 的原始資料轉為 JSON 送交 AI 解析，並具備最安全的 Markdown 防禦清理"""
    batch_input_str = json.dumps(batch_data, ensure_ascii=False)
    prompt = template.replace("{batch_input}", batch_input_str)
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        ai_text = response.text.strip()
        
        # 安全防禦機制：用最簡單的 replace 替換掉可能破壞 JSON 解析的 Markdown 區塊
        if ai_text.startswith("```"):
            ai_text = ai_text.replace("```json", "")
            ai_text = ai_text.replace("```", "")
            
        ai_text = ai_text.strip()
        
        result_list = json.loads(ai_text)
        return result_list
        
    except json.JSONDecodeError as je:
        print(f"AI 回傳資料解析 JSON 失敗: {je}")
        return []
    except Exception as e:
        print(f"AI 批次解析發生錯誤: {e}")
        return []
