import os
import json
import requests
import urllib3
import time
import glob

# 關閉 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_content(config, page=None):
    """通用連線模組，支援 GET/POST 與自訂標頭"""
    url = config.get("url_pattern")
    if page and "{page}" in url:
        url = url.replace("{page}", str(page))
    
    headers = config.get("headers", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    method = config.get("method", "GET").upper()
    payload = config.get("payload", {})
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=payload if method == "POST" else None,
            params=payload if method == "GET" else None,
            verify=False,
            timeout=15
        )
        response.encoding = response.apparent_encoding
        return response.text
    except Exception as e:
        print(f"      [錯誤] 連線失敗: {e}")
        return None

def main():
    print("啟動通用化模組爬蟲...\n")
    config_files = sorted(glob.glob("configs/web*.json"))
    base_output_dir = "scraped_pages"
    os.makedirs(base_output_dir, exist_ok=True)

    for config_file in config_files:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        site_name = config.get("site_name", "Unknown")
        print(f"處理任務: {site_name}")
        
        site_output_dir = os.path.join(base_output_dir, site_name)
        os.makedirs(site_output_dir, exist_ok=True)
        
        start_page = config.get("start_page", 1)
        end_page = config.get("end_page", 1)
        delay = config.get("delay", 0.5)
        
        for page in range(start_page, end_page + 1):
            print(f"      -> 抓取頁面 {page}...")
            content = fetch_content(config, page)
            if content:
                with open(os.path.join(site_output_dir, f"page_{page}.html"), "w", encoding="utf-8") as f:
                    f.write(content)
            time.sleep(delay)
    print("所有任務執行完畢。")

if __name__ == "__main__":
    main()
