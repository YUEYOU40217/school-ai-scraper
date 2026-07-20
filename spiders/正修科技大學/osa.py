import os
import time
from bs4 import BeautifulSoup

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "學務處公告_AI格式"
    delay = 1.0
    
    # 針對第 1 到第 3 頁進行迴圈爬取
    for page in range(1, 4):
        list_url = f"https://osa.csu.edu.tw/p/403-1069-195-{page}.php?Lang=zh-tw"
        print(f"      [{category}] 開始抓取列表第 {page} 頁: {list_url}")
        
        # 使用引擎提供的 fetch_content 抓取列表頁 HTML
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
            date = "N/A"
            
            # 處理相對路徑
            if link.startswith("/"):
                link = "https://osa.csu.edu.tw" + link
            
            # 過濾器：判斷是否為學務處內容 (osa.csu.edu.tw)
            if "osa.csu.edu.tw" in link:
                try:
                    # 進入內頁抓取，使用引擎的 fetch_content
                    inner_html = fetch_content(link)
                    if inner_html:
                        inner_soup = BeautifulSoup(inner_html, "html.parser")
                        date_tag = inner_soup.find("i", class_="mdate")
                        if date_tag:
                            date = date_tag.text.strip()
                except Exception as e:
                    print(f"         -> [連線內頁失敗] {link}")
                
                # 點擊內頁後設定小延遲，避免伺服器阻擋
                time.sleep(0.5)
            else:
                print(f"         -> [跳過外部連結] {title}")
            
            # 將資料組裝成你要求的 DIV 結構
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
        
        # 爬蟲親自負責命名與存檔，每一頁獨立存成一個檔案
        if page_output_html:
            filename = f"{category}_p{page}.html"
            file_path = os.path.join(site_output_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_output_html)
            
            print(f"         -> [成功存檔] {filename}")
            
        # 換下一頁前設定延遲
        time.sleep(delay)
