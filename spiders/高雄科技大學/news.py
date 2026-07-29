import os
import time
from bs4 import BeautifulSoup

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "最新消息"
    delay = 1.0
    
    for page in range(1, 4):
        target_url = f"https://www.nkust.edu.tw/p/422-1000-1001-{page}.php?Lang=zh-tw"
        print(f"      [{category}] 開始抓取列表第 {page} 頁: {target_url}")
        
        list_html = fetch_content(target_url)
        
        if not list_html:
            print(f"         -> [抓取失敗] 無法取得第 {page} 頁內容")
            continue
            
        soup = BeautifulSoup(list_html, "html.parser")
        

        target_block = soup.find("div", id="pageptlist")
        
        if target_block:
            for a_tag in target_block.find_all("a"):
                link = a_tag.get("href")
                if link:
                    link = link.strip().replace(" ", "").replace("%20", "")
                    if link.startswith("/"):
                        link = "https://www.nkust.edu.tw" + link
                    a_tag["href"] = link
            

            page_output_html = str(target_block)
            
            filename = f"{category}_p{page}.html"
            file_path = os.path.join(site_output_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_output_html)
            
            print(f"         -> [成功存檔] {filename}")
        else:
            print(f"         -> [解析失敗] 找不到 id 為 pageptlist 的區塊")
                
        time.sleep(delay)
