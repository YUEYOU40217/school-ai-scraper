import os
import time

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "學務處"
    delay = 1.0
    
    for page in range(1, 4):
        target_url = f"https://osa.nkust.edu.tw/p/403-1154-11-{page}.php?Lang=zh-tw"
        print(f"      [{category}] 開始抓取列表第 {page} 頁: {target_url}")
        
        list_html = fetch_content(target_url)
        
        if not list_html:
            print(f"         -> [抓取失敗] 無法取得第 {page} 頁內容")
            continue
            
        # 不做任何 BeautifulSoup 解析與裁剪，直接將整頁 HTML 寫入檔案
        filename = f"{category}_p{page}.html"
        file_path = os.path.join(site_output_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(list_html)
        
        print(f"         -> [成功存檔] {filename}")
                
        time.sleep(delay)
