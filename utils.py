import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import time

# 關閉不安全連線的 SSL 警告（避免學校舊憑證導致報錯）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 偽裝成正常的瀏覽器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def get_robust_session():
    """建立具備自動重試機制的強固型 Session"""
    session = requests.Session()
    # 遇到 500, 502, 503, 504 伺服器錯誤時，自動最多重試 3 次，避免學校網站突然卡頓
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update(HEADERS)
    return session

def fetch_links_smart(url):
    """抓取目標網址中的所有連結與周邊文字 (內建智慧避障)"""
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
        
        # 🛑 智慧避障黑名單：自動忽略這些明顯不是公告的常駐導覽按鈕
        ignore_keywords = [
            "首頁", "english", "在校生", "家長", "校友", "行事曆", "校史", 
            "交通指引", "網站導覽", "sitemap", "login", "登入", "facebook", 
            "instagram", "youtube", "隱私權政策", "聯絡我們"
        ]

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            
            # 1. 擋掉無效的腳本與功能連結
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
                
            full_url = urljoin(url, href)
            
            link_text = a_tag.get_text(strip=True)
            if not link_text:
                link_text = a_tag.get('title', '').strip()
                
            # 2. 擋掉沒有文字的空連結
            if not link_text:
                continue
                
            # 3. 🛡️ 啟動避障：如果連結文字太短，或是屬於黑名單，直接跳過不爬，節省超多時間！
            link_text_lower = link_text.lower()
            if any(keyword in link_text_lower for keyword in ignore_keywords):
                continue
            if len(link_text) <= 2: # 公告標題通常不會只有一兩個字
                continue

            # 抓取連結附近的文字作為「列表頁週邊文字」（幫助 AI 判斷日期）
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
    """進入公告內頁，把所有純文字抓下來"""
    session = get_robust_session()
    try:
        # 遇到附件直接跳過不下載，避免卡死
        if url.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar')):
            return "【此為檔案附件，已略過內文抓取】"

        response = session.get(url, timeout=30, verify=False)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除不需要的腳本與樣式標籤，減少雜訊
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        text = soup.get_text(separator='\n', strip=True)
        # 限制字數，避免單一頁面過長塞爆 AI 的 Token 限制
        return text[:3000]
        
    except Exception as e:
        print(f"[警告] 略過無法抓取的內文 {url}")
        return "無法取得內文。"

def process_ai_batch(batch, template, client):
    """將一批資料送給 Gemini 進行精準過濾與格式化 (帶有打死不退的防禦機制)"""
    batch_json_str = json.dumps(batch, ensure_ascii=False, indent=2)
    prompt = template.replace("{batch_input}", batch_json_str)
    
    max_retries = 5  # 最多給 AI 伺服器 5 次機會
    
    for attempt in range(max_retries):
        try:
            # 🚀 升級使用 gemini-3.1-flash-lite，速度更快、更不容易塞車！
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                }
            )
            
            result = json.loads(response.text)
            return result
            
        except Exception as e:
            print(f"   ⚠️ [AI 處理失敗] 第 {attempt + 1}/{max_retries} 次嘗試發生異常。")
            
            if attempt < max_retries - 1:
                # 遇到 503 塞車，自動遞增等待時間 (15秒, 30秒, 45秒...)
                sleep_time = (attempt + 1) * 15
                print(f"   ⏳ 伺服器忙碌中，等待 {sleep_time} 秒後重新發送本批資料...")
                time.sleep(sleep_time)
            else:
                print("   ❌ 已達到最大重試次數，Google 伺服器持續無回應，本批資料跳過。")
                return []
