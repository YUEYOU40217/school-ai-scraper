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

# 關閉常規的憑證警告文字
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_robust_session():
    """建立帶有重試機制的穩定 requests Session"""
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
    """自動尋找網頁中帶有日期的公告連結 (含靜動態智慧切換與深度解析)"""
    resp_text = None
    scraper_api_key = os.environ.get("SCRAPER_API_KEY")
    
    # 優先防線：使用 Scraper API 代理連線
    if scraper_api_key:
        print(f"[跳板模式] 正在透過 Scraper API 連線至: {target_url}")
        proxy_url = "https://api.scraperapi.com/"
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
            # 第一彈：常規 Session 連線
            resp = session.get(target_url, timeout=15, verify=False)
            resp.encoding = resp.apparent_encoding
            resp_text = resp.text
        except Exception as e:
            print(f" [第一彈 Session 連線失敗] 錯誤原因: {e}，切換獨立模式...")
            try:
                # 第二彈：獨立 requests 連線
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                resp = requests.get(target_url, headers=headers, timeout=15, verify=False)
                resp.encoding = resp.apparent_encoding
                resp_text = resp.text
            except Exception as e2:
                print(f"[第二彈 獨立連線也失敗] 錯誤原因: {e2}。")
                print("[啟動終極第三彈] 使用底層 urllib 建立不驗證 SSL 上下文強行突破...")
                try:
                    # 第三彈：使用 Python 最底層的 urllib 強行突破
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

    # 狀態旗標，確保動態核心頂多執行一次
    drission_used = False
    
    while True:
        try:
            soup = BeautifulSoup(resp_text if resp_text else "", "html.parser")
            source_name = soup.title.get_text(strip=True) if soup.title else "未命名網頁"
            links = []
            
            all_a_tags = soup.find_all('a')
            garbage_words = ["跳到", "主要內容", "previous", "next", "首頁", "返回", "coreui"]
            
            for a_tag in all_a_tags:
                href = a_tag.get('href')
                title = a_tag.get_text(strip=True)
                
                # 過濾明顯無效的連結與標題
                if not href or not title or len(title) < 5: 
                    continue
                    
                if href.startswith('#') or any(w in title.lower() for w in garbage_words):
                    continue
                    
                # 轉為絕對網址
                full_url = urljoin(target_url, href)
                
                parent = a_tag.parent
                row_text = ""
                date_str = "0000-00-00"
                
                # 深度探索：往上找 6 層以捕捉置頂公告或複雜結構的日期
                for _ in range(6):
                    if parent:
                        row_text = parent.get_text(separator=' ', strip=True)
                        date_match = re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})', row_text)
                        if date_match:
                            date_str = date_match.group(1)
                            break
                        parent = parent.parent
                
                # 沒日期的跳過
                if date_str == "0000-00-00":
                    continue
                    
                links.append({
                    "title": title, 
                    "href": full_url, 
                    "row_text": row_text,
                    "date": date_str
                })
            
            # 【終極第四彈：DrissionPage 動態補救防線】
            if not links and not drission_used:
                print("[靜態防線未取得有效內容] 偵測到公告項目為空，啟動第四彈：DrissionPage 自動化瀏覽器核心強行突破...")
                try:
                    from DrissionPage import ChromiumPage, ChromiumOptions
                    co = ChromiumOptions().auto_port()
                    co.headless(True)  # 背景執行
                    
                    page = ChromiumPage(co)
                    page.get(target_url)
                    
                    # 智慧等待 a 標籤載入，並多給予時間讓動態 JS 渲染完成
                    page.wait.ele_loaded('tag:a', timeout=10)
                    page.wait(2) 
                    
                    resp_text = page.html  # 將完整渲染後的 DOM 丟回
                    drission_used = True   
                    page.quit()
                    
                    print("[第四彈] DrissionPage 成功取得渲染後的網頁原始碼，重新進入解析流程。")
                    continue               
                except Exception as ed:
                    print(f"[第四彈 DrissionPage 異常] 錯誤原因: {ed}")
                    if 'page' in locals():
                        page.quit()
                        
            return source_name, links
            
        except Exception as e:
            print(f"抓取清單解析失敗: {e}")
            if not drission_used:
                print("[解析異常補救] 嘗試啟動第四彈：DrissionPage...")
                try:
                    from DrissionPage import ChromiumPage, ChromiumOptions
                    co = ChromiumOptions().auto_port()
                    co.headless(True)
                    page = ChromiumPage(co)
                    page.get(target_url)
                    page.wait.ele_loaded('tag:a', timeout=10)
                    page.wait(2)
                    resp_text = page.html
                    drission_used = True
                    page.quit()
                    continue
                except Exception as ed:
                    print(f"[第四彈 DrissionPage 補救異常] 錯誤原因: {ed}")
                    if 'page' in locals():
                        page.quit()
            return "抓取失敗", []

def process_ai_batch(titles_list, template, client):
    """將公告標題分批送交給 Gemini 進行關鍵字萃取"""
    prompt = template.replace("{batch_input}", "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles_list)]))
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        # 強化版 JSON 解析防線
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
            
        return [{"keywords": ["解析失敗"]} for _ in titles_list]
