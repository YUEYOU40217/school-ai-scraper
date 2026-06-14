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

# 關閉常規安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_robust_session():
    """建立具有重試機制的強健連線 Session"""
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
    """【零過濾全面撈取版】自動尋找網頁中可能的公告連結與其上下文周邊文字"""
    resp_text = None
    scraper_api_key = os.environ.get("SCRAPER_API_KEY")
    
    # 優先防線：使用 Scraper API 代理連線
    if scraper_api_key:
        print(f"[跳板模式] 正在透過 Scraper API 連線至: {target_url}")
        proxy_url = "[https://api.scraperapi.com/](https://api.scraperapi.com/)"
        payload = {
            'api_key': scraper_api_key,
            'url': target_url
        }
        try:
            resp = requests.get(proxy_url, params=payload, timeout=30)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding
                resp_text = resp.text
                print("[跳板模式] 成功取得網頁原始碼。")
            else:
                print(f"[跳板模式失敗] 狀態碼: {resp.status_code}，切換回原有機制...")
        except Exception as e:
            print(f"[跳板模式異常] 錯誤原因: {e}，切換回原有機制...")

    # 原有三重保險連線機制
    if not resp_text:
        try:
            # 第一彈：Session 連線
            resp = session.get(target_url, timeout=15, verify=False)
            resp.encoding = resp.apparent_encoding
            resp_text = resp.text
        except Exception as e:
            print(f"[第一彈 Session 連線失敗] 錯誤原因: {e}，切換獨立模式...")
            try:
                # 第二彈：獨立 requests 連線
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                resp = requests.get(target_url, headers=headers, timeout=15, verify=False)
                resp.encoding = resp.apparent_encoding
                resp_text = resp.text
            except Exception as e2:
                print(f"[第二彈 獨立連線也失敗] 錯誤原因: {e2}。")
                print("[啟動終極第三彈] 使用底層 urllib 強行突破...")
                try:
                    # 第三彈：使用 Python 最底層的 urllib，強制建立不驗證的 SSL 上下文
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
                    print(f"[三重保險皆失敗] 該網址真的無法連線: {e3}")
                    return "抓取失敗", []

    try:
        soup = BeautifulSoup(resp_text, "html.parser")
        source_name = soup.title.get_text(strip=True) if soup.title else "未命名網頁"
        links = []
        seen_urls = set()
        all_a_tags = soup.find_all('a')
        
        # 只剔除非功能性的主要跳轉導覽錨點，其餘一概保留
        garbage_words = ["跳到", "主要內容區", "跳至主要內容"]
        
        for a_tag in all_a_tags:
            href = a_tag.get('href')
            title = a_tag.get_text(strip=True)
            
            if not href or not title or len(title) < 2:  # 放寬字數限制
                continue
                
            if href.startswith('#') or any(w in title.lower() for w in garbage_words):
                continue
                
            full_url = urljoin(target_url, href)
            if full_url in seen_urls: 
                continue
                
            # 向上爬取 3 層父節點，取得最完整的上下文排版字串（確保包含欄位日期）
            parent = a_tag.parent
            row_text = ""
            for _ in range(3):
                if parent:
                    row_text = parent.get_text(separator=' ', strip=True)
                    if len(row_text) > len(title):
                        break
                    parent = parent.parent
            
            # 僅供日誌參考的預提取日期（若偵測失敗也不過濾，直接交由 AI 進階分析）
            date_match = re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})', row_text)
            date_str = date_match.group(1) if date_match else "未偵測到日期"
                
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

def process_ai_batch(titles_list, template, client):
    """將包含上下文與標題的資訊打包送給 Gemini，並嚴格要求回傳對應格式的 JSON"""
    prompt = template.replace("{batch_input}", "\n".join([f"{i+1}. {item}" for i, item in enumerate(titles_list)]))
    try:
        # 使用 Google GenAI SDK 官方呼叫方式
        response = client.models.generate_content(
            model='gemini-2.5-flash',
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
            
        # 回傳預設解析失敗資料
        return [{"keywords": ["解析失敗"], "is_allowed_year": False, "extracted_date": "1970-01-01"} for _ in titles_list]
