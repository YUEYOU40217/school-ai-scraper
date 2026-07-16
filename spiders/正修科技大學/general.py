import os
import time
from bs4 import BeautifulSoup

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "總務處公告"
    delay = 1.0
    
    for page in range(1, 4):
        target_url = f"https://general.csu.edu.tw/p/403-1070-418-{page}.php?Lang=zh-tw"
        print(f"      [{category}] 開始抓取第 {page} 頁: {target_url}")
        
        list_html = fetch_content(target_url)
        if not list_html: 
            continue
        
        soup = BeautifulSoup(list_html, "html.parser")
        links = soup.select(".mtitle a")
        
        for idx, link in enumerate(links):
            inner_url = link.get("href")
            if not inner_url: 
                continue
            
            print(f"         -> 深入內頁: {inner_url}")
            inner_html = fetch_content(inner_url)
            
            if inner_html:
                filename = f"{category}_p{page}_{idx}.html"
                file_path = os.path.join(site_output_dir, filename)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(inner_html)
                
                print(f"         -> [成功存檔] {filename}")
                    
            time.sleep(delay)
