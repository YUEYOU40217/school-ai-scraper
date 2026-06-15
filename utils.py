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

# 初始化全域連線 Session
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
                
            # 抓取連結上下三層父節點的文字（一分不差保留畫面上周邊文字）
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
        
        # 只拔除腳本與樣式，其餘完全保留
        for element in soup(["script", "style"]):
            element.extract()
        
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        
        return text if text else "[此網頁無文字內容]"
    except Exception as e:
        return f"[內頁文字解析異常]: {e}"

def process_ai_batch(batch_data, template, client):
    """將含有「標題+上下文+內頁內文」的資料組合送交 Gemini 解析"""
    batch_inputs = []
    for i, item in enumerate(batch_data):
        title = item['title']
        url = item['url']
        list_context = item.get('list_context', '無週邊文字')
        full_content = item.get('content', '無內文資料')
        
        batch_inputs.append(
            f"項目 {i+1}:\n"
            f"  - 標題: {title}\n"
            f"  - 網址: {url}\n"
            f"  - 列表頁週邊文字: {list_context}\n"
            f"  - 內頁完整內文: {full_content}\n"
            f"----------------------------------------"
        )

    prompt = template.replace("{batch_input}", "\n".join(batch_inputs))
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
        return []
