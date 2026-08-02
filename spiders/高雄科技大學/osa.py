import os
import time
from bs4 import BeautifulSoup

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
            
        soup = BeautifulSoup(list_html, "html.parser")
        
        # 尋找目標區塊
        target_block = soup.find("div", id="pageptlist")
        
        if target_block:
            for a_tag in target_block.find_all("a"):
                link = a_tag.get("href")
                if link:
                    # 清理網址中的空白
                    link = link.strip().replace(" ", "").replace("%20", "")

                    # 修正縮排並加入判斷：如果是相對路徑，則補上主網域
                    if link.startswith("/"):
                        link = "https://osa.nkust.edu.tw" + link
                        
                    a_tag["href"] = link
            
            # 將目標區塊轉回 HTML 字串
            page_output_html = str(target_block)
            
            filename = f"{category}_p{page}.html"
            file_path = os.path.join(site_output_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_output_html)
            
            print(f"         -> [成功存檔] {filename}")
        else:
            print(f"         -> [解析失敗] 找不到 id 為 pageptlist 的區塊")
                
        time.sleep(delay)
