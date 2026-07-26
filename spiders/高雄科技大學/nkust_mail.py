import os
import time
from bs4 import BeautifulSoup

def run(site_output_dir, fetch_content):
    # 【修正】使用主程式傳進來的安全路徑，絕對不要寫死絕對路徑
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "高科大郵件與公告"
    delay = 1.0
    
    target_url = "https://officemail.nkust.edu.tw/mail"
    print(f"      [{category}] 開始抓取單頁: {target_url}")
    
    page_html = fetch_content(target_url)
    
    if not page_html:
        print(f"         -> [抓取失敗] 無法取得該頁面內容")
        return
        
    soup = BeautifulSoup(page_html, "html.parser")
    
    # 尋找主要的容器或整頁核心
    target_block = soup.find("div", class_="wrap") or soup.find("body")
    
    if target_block:
        # 清洗區塊內的相對網址
        for a_tag in target_block.find_all("a"):
            link = a_tag.get("href")
            if link:
                link = link.strip().replace(" ", "").replace("%20", "")
                if link.startswith("/"):
                    link = "https://officemail.nkust.edu.tw" + link
                a_tag["href"] = link 
        
        page_output_html = str(target_block)
        
        # 嚴格使用 site_output_dir 進行存檔
        filename = "officemail_p1.html"
        file_path = os.path.join(site_output_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(page_output_html)
        
        print(f"         -> [成功存檔] {filename}")
    else:
        print(f"         -> [解析失敗] 找不到對應的網頁結構")
            
    time.sleep(delay)
