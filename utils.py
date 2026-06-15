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
    
    # 優先防線：如果環境變數有 ScraperAPI Key，就走跳板防封鎖
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

    # 第一重後援：標準 Requests Session (帶重試機制)
    try:
        resp = session.get(target_url, timeout=15, verify=False)
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception as e:
        # 第二重後援：乾淨的全新 Requests 請求 (無視乾淨 Header 阻擋)
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            resp = requests.get(target_url, headers=headers, timeout=15, verify=False)
            resp.encoding = resp.apparent_encoding
            return resp.text
        except Exception as e2:
            # 第三重後援：最底層的 urllib 原生連線 (強行繞過部分頑固防火牆)
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
    """【第一層】全量掃描網頁，尋找工作區內所有帶有日期的公告連結"""
    resp_text = fetch_html_robust(target_url)
    if not resp_text:
        return "抓取失敗", []

    try:
        soup = BeautifulSoup(resp_text, "html.parser")
        source_name = soup.title.get_text(strip=True) if soup.title else "未命名網頁"
        links = []
        seen_urls = set()
        all_a_tags = soup.find_all('a')
        
        # 過濾常見的無效導覽字眼
        garbage_words = ["跳到", "主要內容", "previous", "next", "首頁", "返回", "coreui"]
        
        for a_tag in all_a_tags:
            href = a_tag.get('href')
            title = a_tag.get_text(strip=True)
            
            # 標題太短或根本沒超連結的直接剔除
            if not href or not title or len(title) < 5: 
                continue
                
            # 排除錨點與導覽垃圾連結
            if href.startswith('#') or any(w in title.lower() for w in garbage_words):
                continue
                
            # 補全相對路徑網址
            full_url = urljoin(target_url, href)
            if full_url in seen_urls: 
                continue
                
            parent = a_tag.parent
            row_text = ""
            date_str = "0000-00-00"
            
            # 往上回溯三層父節點，尋找鄰近該連結的日期標籤
            for _ in range(3):
                if parent:
                    row_text = parent.get_text(separator=' ', strip=True)
                    date_match = re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})', row_text)
                    if date_match:
                        date_str = date_match.group(1)
                        break
                    parent = parent.parent
            
            # 如果附近完全找不到任何日期，代表這不是公告，不予抓取
            if date_str == "0000-00-00":
                continue
                
            links.append({
                "title": title, 
                "href": href, 
                "row_text": row_text,
                "date": date_str
            })
            seen_urls.add(full_url)
                    
        return source_name, links
    except Exception as e:
        print(f"抓取清單解析失敗: {e}")
        return "抓取失敗", []

def fetch_detail_content(url):
    """【第二層】深入公告內頁，刮除雜質並抓取純淨的內文"""
    html = fetch_html_robust(url)
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # 暴力拔除網頁頁首、頁尾、選單、腳本等無關內容
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.extract()
        
        # 取得內頁純文字並壓縮空白
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        
        # 限制字數在前 800 字（通常重點精華都在前段，防止餵給 AI 時 token 爆炸）
        return text[:800]
    except:
        return ""

def process_ai_batch(batch_data, template, client):
    """將含有「標題+詳細內文」的資料組合，批次送交 Gemini 解析"""
    batch_inputs = []
    for i, item in enumerate(batch_data):
        title = item['title']
        content_snippet = item.get('content', '無內文資料')
        # 把豐富的內頁內容塞進 Prompt
        batch_inputs.append(f"{i+1}. 標題: {title}\n   內文詳細內容: {content_snippet}")

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
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"【AI 原始回覆內容】:\n{response.text}")
            
        return [{"keywords": ["解析失敗"]} for _ in batch_data]
