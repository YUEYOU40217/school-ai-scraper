import os
import time

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "首頁全部公告"
    delay = 1.0
    
    # 只抓列表頁的第 1 到 3 頁
    for page in range(1, 4):
        target_url = f"https://www.csu.edu.tw/p/403-1000-13-{page}.php?Lang=zh-tw"
        print(f"      [{category}] 開始抓取列表第 {page} 頁: {target_url}")
        
        # 直接抓取列表頁的 HTML
        list_html = fetch_content(target_url)
        
        # 爬蟲親自負責命名與存檔
        if list_html:
            # 檔名直接標示頁碼即可
            filename = f"{category}_p{page}.html"
            file_path = os.path.join(site_output_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(list_html)
            
            print(f"         -> [成功存檔] {filename}")
                
        time.sleep(delay)
