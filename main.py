import os
import json
import requests
import urllib3
import time
import glob

# 關閉 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_content(config, page=None):
    """通用連線模組，支援 GET/POST、自訂標頭與 "Nope" 預設值過濾"""
    url = config.get("url_pattern")
    if page and "{page}" in url:
        url = url.replace("{page}", str(page))
    
    # 處理 Headers：如果是 "Nope" 或沒填，就用預設的 User-Agent
    raw_headers = config.get("headers")
    if raw_headers == "Nope" or not raw_headers:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    else:
        headers = raw_headers

    # 處理 Method：如果是 "Nope" 或沒填，預設為 GET
    raw_method = config.get("method")
    method = "GET" if (raw_method == "Nope" or not raw_method) else raw_method.upper()
    
    # 處理 Payload：如果是 "Nope" 或沒填，預設為空字典
    raw_payload = config.get("payload")
    payload = {} if (raw_payload == "Nope" or not raw_payload) else raw_payload
    
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
    print("啟動極簡通用化模組爬蟲...\n")
    config_files = sorted(glob.glob("configs/web*.json")) # 掃描所有設定檔
    base_output_dir = "scraped_pages"
    os.makedirs(base_output_dir, exist_ok=True) # 建立輸出根目錄

    if not config_files:
        print("[錯誤] 找不到任何設定檔，請確認 configs 資料夾與檔案是否存在。")
        return

    for config_file in config_files:
        print("-" * 50)
        print(f"讀取任務: {config_file}")
        
        with open(config_file, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                print(f"      [錯誤] {config_file} 格式錯誤，略過此任務。")
                continue
        
        site_name = config.get("site_name", "Unknown_Site")
        print(f"目標網站: {site_name}")
        
        # 建立網站專屬輸出資料夾
        site_output_dir = os.path.join(base_output_dir, site_name)
        os.makedirs(site_output_dir, exist_ok=True)
        
        # 解析分頁與延遲參數（相容 "Nope"）
        start_page = config.get("start_page", 1)
        end_page = config.get("end_page", 1)
        
        raw_delay = config.get("delay")
        delay = 0.5 if (raw_delay == "Nope" or raw_delay is None) else float(raw_delay)
        
        # 開始執行翻頁抓取迴圈
        for page in range(start_page, end_page + 1):
            print(f"      -> 正在抓取第 {page} 頁...")
            content = fetch_content(config, page)
            
            if content:
                file_path = os.path.join(site_output_dir, f"page_{page}.html")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            
            time.sleep(delay) # 防爬蟲封鎖的延遲時間
            
        print(f"      [成功] 任務完成，資料已儲存至: {site_output_dir}")

    print("-" * 50)
    print("所有任務執行完畢！")

if __name__ == "__main__":
    main()
