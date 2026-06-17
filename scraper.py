import os
import requests
import urllib3
import time

# 停用不安全連線警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_content(config, page=None):
    url = config.get("url_pattern")
    if page and "{page}" in url:
        url = url.replace("{page}", str(page))
    
    raw_headers = config.get("headers")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"} if (raw_headers == "Nope" or not raw_headers) else raw_headers

    raw_method = config.get("method")
    method = "GET" if (raw_method == "Nope" or not raw_method) else raw_method.upper()
    
    raw_payload = config.get("payload")
    payload = None if (raw_payload == "Nope" or not raw_payload) else raw_payload
    
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
    
    start_page = config.get("start_page", 1)
    end_page = config.get("end_page", 1)
    raw_delay = config.get("delay")
    delay = 0.5 if (raw_delay == "Nope" or raw_delay is None) else float(raw_delay)
    
    for page in range(start_page, end_page + 1):
        content = fetch_content(config, page)
        if content:
            file_path = os.path.join(site_output_dir, f"page_{page}.html")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"      -> 已儲存第 {page} 頁: {file_path}")
        time.sleep(delay)
        
    return site_output_dir
