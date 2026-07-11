import os
import requests
import urllib3
import time

# 停用不安全連線警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 核心修改：從環境變數讀取爬蟲專用 API Key
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

def fetch_content(url, config):
    raw_headers = config.get("headers")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"} if (raw_headers == "Nope" or not raw_headers) else raw_headers

    raw_method = config.get("method")
    method = "GET" if (raw_method == "Nope" or not raw_method) else raw_method.upper()
    
    raw_payload = config.get("payload")
    payload = {} if (raw_payload == "Nope" or not raw_payload) else raw_payload
    
    # -------------------------------------------------------------
    # 【API Key 整合邏輯】
    # -------------------------------------------------------------
    if SCRAPER_API_KEY:
        # 作法 A：如果是當作 Header 傳送
        # headers["X-Scraper-API-Key"] = SCRAPER_API_KEY
        # headers["Authorization"] = f"Bearer {SCRAPER_API_KEY}"
        
        # 作法 B：如果是串接轉發代理服務
        # proxy_params = {"api_key": SCRAPER_API_KEY, "url": url}
        # if method == "GET":
        #     payload.update(proxy_params)
        
        # 作法 C：直接附加在網址後方作為 Query String
        # if "?" in url:
        #     url = f"{url}&apikey={SCRAPER_API_KEY}"
        # else:
        #     url = f"{url}?apikey={SCRAPER_API_KEY}"
        pass # （保留你的 API 判斷邏輯，為了避免每頁都印出提示，這裡預設 pass）
    # -------------------------------------------------------------

    try:
        if method == "POST":
            response = requests.post(url, headers=headers, json=payload, verify=False, timeout=15)
        else:
            response = requests.get(url, headers=headers, params=payload, verify=False, timeout=15)
            
        response.encoding = response.apparent_encoding
        return response.text
    except Exception as e:
        print(f"      [錯誤] 連線失敗: {e}")
        return None

def run_spider(config, base_output_dir):
    site_name = config.get("site_name", "Unknown_Site")
    
    # 建立專屬資料夾
    site_output_dir = os.path.join(base_output_dir, site_name)
    os.makedirs(site_output_dir, exist_ok=True)
    print(f"目標網站: {site_name} -> 存檔位置: {site_output_dir}/")
    
    # 讀取全域設定
    raw_delay = config.get("delay")
    delay = 0.5 if (raw_delay == "Nope" or raw_delay is None) else float(raw_delay)
    
    # 讀取任務清單
    tasks = config.get("tasks", [])
    if not tasks:
        print("      [警告] 設定檔中找不到 tasks 清單，請確認 JSON 格式。")
        return site_output_dir

    # 迴圈處理每一個公告分類
    for task in tasks:
        category = task.get("category", "未分類")
        url_pattern = task.get("url_pattern")
        start_page = task.get("start_page", 1)
        end_page = task.get("end_page", 1)
        
        print(f"   -> 開始抓取類別: {category}")
        
        for page in range(start_page, end_page + 1):
            # 組合目標網址
            if url_pattern and "{page}" in url_pattern:
                url = url_pattern.replace("{page}", str(page))
            else:
                url = url_pattern
                
            content = fetch_content(url, config)
            if content:
                # 檔名前方加上 category，避免不同公告的相同頁碼互相覆蓋
                file_path = os.path.join(site_output_dir, f"{category}_page_{page:04d}.html")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"      -> 已儲存 {category} 第 {page} 頁: {file_path}")
            
            time.sleep(delay)
            
    return site_output_dir
