import os
import time

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    delay = 1.0
    
    # 將你要抓取的兩個網址與對應的檔名寫成清單
    targets = [
        {
            "filename": "學務處首頁.html",
            "url": "https://osa.csu.edu.tw/"
        },
        {
            "filename": "學務處公告_p1.html",
            "url": "https://osa.csu.edu.tw/p/403-1069-195-1.php?Lang=zh-tw"
        }
    ]
    
    for target in targets:
        url = target["url"]
        filename = target["filename"]
        
        print(f"      開始抓取: {url}")
        
        # 呼叫你原本的 fetch_content 函數來取得 HTML
        html_content = fetch_content(url)
        
        # 爬蟲負責命名與存檔
        if html_content:
            file_path = os.path.join(site_output_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print(f"         -> [成功存檔] {filename}")
        else:
            print(f"         -> [抓取失敗] fetch_content 未回傳內容 ({filename})")
                
        time.sleep(delay)
