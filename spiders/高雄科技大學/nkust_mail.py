import os
import time
import requests
import urllib3

# 停用不安全連線警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "高科大郵件公告"
    delay = 1.0
    api_url = "https://officemail.nkust.edu.tw/mail/ReadIndex"
    
    print(f"      [{category}] 開始請求 API: {api_url}")
    
    for page in range(1, 6):
        payload = {
            "page": page,
            "pageSize": 20
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        
        try:
            response = requests.post(api_url, data=payload, headers=headers, verify=False, timeout=10)
            
            if response.status_code == 200:
                json_data = response.json()
                data_list = json_data.get("Data", [])
                
                if not data_list:
                    print(f"         -> [第 {page} 頁] 沒有資料了，停止抓取。")
                    break
                    
                page_output_html = ""
                
                for item in data_list:
                    mail_id = item.get("Id", "")
                    sender = item.get("Sender", "")
                    subject = item.get("Subject", "").strip()
                    send_date = item.get("SendDate", "Nope").strip()
                    
                    title = f"[{sender}] {subject}"
                    
                    link = f"https://officemail.nkust.edu.tw/mail/Read/{mail_id}"
                    
                    html_block = f"""
<div class="mbox">
    <div class="d-txt">
        <div class="mtitle">
            <i class="mdate before">{send_date} </i>
            <a href="{link}" title="{title}">
                {title}
            </a>
        </div>
    </div>
</div>"""
                    page_output_html += html_block + "\n"
                    
                # 存檔邏輯 (副檔名存回 .html，讓 AI_parser 能夠統一抓取)
                if page_output_html:
                    filename = f"{category}_p{page}.html"
                    file_path = os.path.join(site_output_dir, filename)
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(page_output_html)
                    
                    print(f"         -> [成功存檔] {filename}")
                    
            else:
                print(f"         -> [抓取失敗] 第 {page} 頁，API 回傳狀態碼: {response.status_code}")
                
        except Exception as e:
            print(f"         -> [抓取錯誤] 第 {page} 頁發生異常: {e}")
            
        time.sleep(delay)
