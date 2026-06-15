import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import time

# 關閉不安全連線的 SSL 警告（許多學校網站的安全憑證常常過期或未設定好）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def get_robust_session():
    """建立具備自動重試機制的強固型 Session"""
    session = requests.Session()
    # 遇到 500, 502, 503, 504 等伺服器錯誤時，自動最多重試 3 次
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update(HEADERS)
    return session

def fetch_links_smart(url):
    """抓取目標網址中的所有連結與周邊文字 (強固版)"""
    session = get_robust_session()
    try:
        # timeout 拉長到 30 秒，並設定 verify=False 繞過學校 SSL 憑證問題
        response = session.get(url, timeout=30, verify=False)
        response.raise_for_status()
        response.encoding = response.apparent_encoding 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_tag = soup.find('title')
        source_name = title_tag.text.strip() if title_tag else "未知網頁"
        
        links_data = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
                
            full_url = urljoin(url, href)
            
            link_text = a_tag.get_text(strip=True)
            if not link_text:
                link_text = a_tag.get('title', '').strip()
                
            if not link_text:
                continue

            parent = a_tag.parent
            list_context = parent.get_text(separator=' ', strip=True) if parent else ""

            links_data.append({
                "title": link_text,
                "href": full_url,
                "list_context": list_context
            })
            
        return source_name, links_data

    except Exception as e:
        print(f"[錯誤] 無法抓取連結 {url}: {e}")
        return "錯誤網頁", []

def fetch_detail_content(url):
    """進入公告內頁，把所有純文字抓下來 (強固版)"""
    session = get_robust_session()
    try:
        response = session.get(url, timeout=30, verify=False)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        text = soup.get_text(separator='\n', strip=True)
        return text[:3000]
        
    except Exception as e:
        print(f"[警告] 無法抓取內文 {url}: {e}")
        return "無法取得內文。"

def process_ai_batch(batch, template, client):
    """將一批資料送給 Gemini 進行精準過濾與格式化 (帶有不放棄重試防禦)"""
    batch_json_str = json.dumps(batch, ensure_ascii=False, indent=2)
    prompt = template.replace("{batch_input}", batch_json_str)
    
    max_retries = 5  # 最多給 AI 伺服器 5 次機會
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                }
            )
            
            result = json.loads(response.text)
            return result
            
        except Exception as e:
            print(f"   ⚠️ [AI 處理失敗] 第 {attempt + 1}/{max_retries} 次嘗試失敗。錯誤: {e}")
            
            if attempt < max_retries - 1:
                # 如果是塞車，我們就遞增等待時間 (20秒, 40秒, 60秒...)
                sleep_time = (attempt + 1) * 20
                print(f"   ⏳ [防禦機制啟動] 伺服器忙碌，等待 {sleep_time} 秒後重新發送本批資料...")
                time.sleep(sleep_time)
            else:
                print("   ❌ [嚴重錯誤] 已達到最大重試次數，Google 伺服器持續無回應，本批資料跳過。")
                return []
