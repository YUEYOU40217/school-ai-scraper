import os
import time
import re  # 新增引入正則表達式模組
from bs4 import BeautifulSoup

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "學務處公告_AI格式"
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
            date = "N/A"
            
            # 處理相對路徑
            if link.startswith("/"):
                link = "https://osa.csu.edu.tw" + link
            
            # 過濾器：判斷是否為學務處內容
            if "osa.csu.edu.tw" in link:
                try:
                    inner_html = fetch_content(link)
                    if inner_html:
                        inner_soup = BeautifulSoup(inner_html, "html.parser")
                        
                        # 改良版日期抓取邏輯
                        # 1. 尋找任何帶有 mdate class 的標籤
                        date_tag = inner_soup.find(class_="mdate")
                        if date_tag:
                            # 清除可能多餘的文字，如 "發布日期："
                            date = date_tag.text.replace("發布日期", "").replace(":", "").replace("：", "").strip()
                        
                        # 2. 如果還是找不到 (或抓出來是空的)，使用正則表達式在網頁文字中硬搜
                        if date == "N/A" or not date:
                            match = re.search(r'(20\d{2}[-/]\d{2}[-/]\d{2})', inner_soup.text)
                            if match:
                                date = match.group(1)
                                
                except Exception as e:
                    print(f"         -> [連線內頁失敗] {link}")
                
                time.sleep(0.5)
            else:
                print(f"         -> [跳過外部連結] {title}")
            
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
        
        if page_output_html:
            filename = f"{category}_p{page}.html"
            file_path = os.path.join(site_output_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_output_html)
            
            print(f"         -> [成功存檔] {filename}")
            
        time.sleep(delay)
