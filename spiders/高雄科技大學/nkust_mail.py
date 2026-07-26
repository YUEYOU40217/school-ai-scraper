import os
import time
import requests

# 停用不安全連線警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "高科大郵件與公告"
    delay = 1.0
    
    # 【改變戰術】不抓網頁，直接戳隱藏的資料 API 端點
    api_url = "https://officemail.nkust.edu.tw/mail/ReadIndex"
    print(f"      [{category}] 開始請求 API: {api_url}")
    
    # 模擬 Kendo UI Grid 發送的請求參數 (通常是請求第一頁，每頁10筆)
    payload = {
        "page": 1,
        "pageSize": 10
    }
    
    # 加上 Header 偽裝成是瀏覽器發出的 AJAX 請求
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    
    try:
        # 直接使用 requests 發送 POST 請求
        response = requests.post(api_url, data=payload, headers=headers, verify=False, timeout=10)
        
        if response.status_code == 200:
            # 這次抓回來的大機率是 JSON 格式，我們存成 .json 檔來看看
            filename = "officemail_api_p1.json"
            file_path = os.path.join(site_output_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            print(f"         -> [成功存檔] {filename}")
        else:
            print(f"         -> [抓取失敗] API 回傳狀態碼: {response.status_code}")
            
    except Exception as e:
        print(f"         -> [抓取錯誤] 發生異常: {e}")
            
    time.sleep(delay)
