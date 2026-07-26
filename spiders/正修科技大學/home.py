import os
import time
from bs4 import BeautifulSoup

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "全部公告"
    delay = 1.0
    
    # 只抓列表頁的第 1 到 3 頁
    for page in range(1, 4):
        target_url = f"https://www.csu.edu.tw/p/403-1000-13-{page}.php?Lang=zh-tw"
        print(f"      [{category}] 開始抓取列表第 {page} 頁: {target_url}")
        
        # 抓取列表頁的 HTML
        list_html = fetch_content(target_url)
        
        if not list_html:
            print(f"         -> [抓取失敗] 無法取得第 {page} 頁內容")
            continue
            
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(list_html, "html.parser")
        
        # 【修改重點】直接尋找包含標題與列表的完整大區塊
        # 網頁中該區塊的 class 包含了 module-rcglist，我們以此為定位點
        target_block = soup.find("div", class_="module-rcglist")
        
        if target_block:
            # 順手把這個區塊裡的「相對網址」洗成「絕對網址」，並除掉空白
            # 這樣存下來的 HTML 裡面的網址就都是乾淨、完整的，方便後續推播
            for a_tag in target_block.find_all("a"):
                link = a_tag.get("href")
                if link:
                    link = link.strip().replace(" ", "").replace("%20", "")
                    if link.startswith("/"):
                        link = "https://www.csu.edu.tw" + link
                    a_tag["href"] = link  # 把洗乾淨的網址塞回去
            
            # 將這個切下來的區塊轉回 HTML 字串
            page_output_html = str(target_block)
            
            # 存檔
            filename = f"{category}_p{page}.html"
            file_path = os.path.join(site_output_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_output_html)
            
            print(f"         -> [成功存檔] {filename}")
        else:
            print(f"         -> [解析失敗] 找不到 module-rcglist 區塊")
                
        time.sleep(delay)
