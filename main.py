import os
import json
import requests
import urllib3
import time
import glob

# 關閉 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_html(url):
    """底層連線模組"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        response.encoding = response.apparent_encoding
        return response.text
    except Exception as e:
        print(f"      [錯誤] 連線失敗 ({url}): {e}")
        return None

def process_static_html(config, output_dir):
    """處理單一靜態網頁的規則"""
    url = config.get("url_pattern")
    html_content = fetch_html(url)
    
    if html_content:
        file_path = os.path.join(output_dir, "page.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"      [成功] 單頁 HTML 已儲存至: {file_path}")

def process_api_pagination(config, output_dir):
    """處理無限滾動 / API 分頁的規則 (如正修公告)"""
    url_pattern = config.get("url_pattern")
    start_page = config.get("start_page", 1)
    end_page = config.get("end_page", 1)
    
    for page in range(start_page, end_page + 1):
        # 將樣板中的 {page} 替換為實際頁碼
        target_url = url_pattern.replace("{page}", str(page))
        print(f"      -> 正在抓取第 {page} 頁: {target_url}")
        
        html_content = fetch_html(target_url)
        
        if html_content:
            file_path = os.path.join(output_dir, f"page_{page}.html")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        
        # 避免發送請求過快被封鎖
        time.sleep(0.5)
    
    print(f"      [成功] 共 {end_page - start_page + 1} 頁 HTML 已全數儲存完成。")

def main():
    print("啟動模組化爬蟲排程器...\n")
    
    # 掃描 configs 目錄下所有的 .json 檔案
    config_files = sorted(glob.glob("configs/web*.json"))
    
    if not config_files:
        print("[錯誤] 找不到任何設定檔，請確認 configs 資料夾與檔案是否存在。")
        return

    print(f"共偵測到 {len(config_files)} 個任務設定檔。")
    
    base_output_dir = "scraped_pages"
    os.makedirs(base_output_dir, exist_ok=True)

    # 依序讀取並執行每個設定檔
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
        rule = config.get("rule")
        
        print(f"目標網站: {site_name}")
        print(f"執行規則: {rule}")
        
        # 為該網站建立專屬的輸出資料夾
        site_output_dir = os.path.join(base_output_dir, site_name)
        os.makedirs(site_output_dir, exist_ok=True)
        
        # 根據 rule 呼叫對應的處理函數
        if rule == "static_html":
            process_static_html(config, site_output_dir)
        elif rule == "api_pagination":
            process_api_pagination(config, site_output_dir)
        else:
            print(f"      [警告] 系統尚未支援此規則: {rule}")

    print("-" * 50)
    print("所有任務執行完畢！請至 scraped_pages 資料夾檢視結果。")

if __name__ == "__main__":
    main()
