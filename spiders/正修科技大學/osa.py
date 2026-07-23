import os
import time
import re  
from bs4 import BeautifulSoup

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "學務處公告"
    delay = 1.0
    
    # 針對第 1 到第 3 頁進行迴圈爬取
    for page in range(1, 4):
        list_url = f"https://osa.csu.edu.tw/p/403-1069-195-{page}.php?Lang=zh-tw"
        print(f"      [{category}] 開始抓取列表第 {page} 頁: {list_url}")
        
        list_html = fetch_content(list_url)
        
        if not list_html:
            print(f"         -> [抓取失敗] 無法取得第 {page} 頁內容")
            continue
            
        soup = BeautifulSoup(list_html, "html.parser")
        articles = soup.find_all("div", class_="mtitle")
        
        page_output_html = ""
        
        for article in articles:
            a_tag = article.find("a")
            if not a_tag:
                continue
                
            title = a_tag.text.strip()
            link = a_tag.get("href")
            date = "Nope"

            # 請求之前，第一時間把空白和 %20 去掉
            if link:
                link = link.strip().replace(" ", "").replace("%20", "")
                
            # 處理相對路徑
            if link.startswith("/"):
                link = "https://osa.csu.edu.tw" + link
            
            # 移除網域過濾，所有的連結都會嘗試去抓取內頁的時間
            try:
                inner_html = fetch_content(link)
                if inner_html:
                    inner_soup = BeautifulSoup(inner_html, "html.parser")
                    
                    # 1. 尋找任何帶有 mdate class 的標籤
                    date_tag = inner_soup.find(class_="mdate")
                    if date_tag:
                        # 清除可能多餘的文字
                        date = date_tag.text.replace("發布日期", "").replace(":", "").replace("：", "").strip()
                    
                    # 2. 如果還是找不到 (或抓出來是空的)，使用正則表達式在網頁文字中硬搜
                    if date == "Nope" or not date:
                        match = re.search(r'(20\d{2}[-/]\d{2}[-/]\d{2})', inner_soup.text)
                        if match:
                            date = match.group(1)
                            
            except Exception as e:
                # 遇到外部網站阻擋連線或發生錯誤時，直接印出提示，但不中斷
                print(f"         -> [連線內頁失敗或外部連結] {link}")
            
            time.sleep(0.5)
            
            # 雙重保險，萬一前面的處理結果變成空字串，強制補回 "Nope"
            if not date:
                date = "Nope"
            
            # 所有的公告最後都會跑到這裡被組裝起來
            html_block = f"""
<div class="mbox">
    <div class="d-txt">
        <div class="mtitle">
            <i class="mdate before">{date} </i>
            <a href="{link}" title="{title}">
                {title}
            </a>
        </div>
    </div>
</div>"""
            page_output_html += html_block + "\n"
        
        # 存檔邏輯
        if page_output_html:
            filename = f"{category}_p{page}.html"
            file_path = os.path.join(site_output_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_output_html)
            
            print(f"         -> [成功存檔] {filename}")
            
        time.sleep(delay)
