import os
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "學務處公告"
    delay = 1.0 
    
    for page in range(1, 4):
        list_url = f"https://osa.csu.edu.tw/p/403-1069-195-{page}.php?Lang=zh-tw"
        print(f"      [{category}] 開始抓取列表第 {page} 頁: {list_url}")
        
        list_html = fetch_content(list_url)
        if not list_html: 
            continue
        
        soup = BeautifulSoup(list_html, "html.parser")
        links = soup.select(".mtitle a")
        
        if not links:
            break

        # ==================================================
        # 建立輕量化 HTML 模板開頭
        # ==================================================
        mini_html_content = f"<html><body>\n"

        for idx, link in enumerate(links):
            href = link.get("href")
            # 從列表頁直接抓標題
            title = link.get("title") or link.get_text(strip=True)
            
            if not href: 
                continue
            
            inner_url = urljoin(list_url, href)
            print(f"         -> 深入內頁尋找日期 ({idx+1}/{len(links)}): {inner_url}")
            
            inner_html = fetch_content(inner_url)
            date_str = ""
            
            if inner_html:
                inner_soup = BeautifulSoup(inner_html, "html.parser")
                
                # 策略 A：尋找 RulingDigital 系統常見的日期標籤
                date_tag = inner_soup.find(class_=re.compile(r'mdate|date', re.I))
                if date_tag:
                    date_str = date_tag.get_text(strip=True)
                else:
                    # 策略 B：用正則表達式暴力搜尋 YYYY-MM-DD 或 YYYY/MM/DD
                    match = re.search(r'(202\d[-/]\d{2}[-/]\d{2})', inner_soup.get_text())
                    if match:
                        date_str = match.group(1)
            
            # 防呆：如果真的找不到日期，給個預設格式避免 AI 崩潰
            if not date_str:
                date_str = "2026-01-01" 
            
            # ==================================================
            # 按照你設計的完美結構，把這篇公告塞進輕量化 HTML 中
            # ==================================================
            mini_html_content += f"""
            <div class="mbox">
                <div class="d-txt">
                    <div class="mtitle">
                        <i class="mdate before">{date_str}</i>
                        <a href="{inner_url}" title="{title}">
                            {title}
                        </a>
                    </div>
                </div>
            </div>
            """
            time.sleep(delay)
            
        # 補上 HTML 結尾
        mini_html_content += "</body></html>"
        
        # 存檔：把剛才組合好的「完美結構」寫入單一檔案
        filename = f"{category}_p{page}_lite.html"
        file_path = os.path.join(site_output_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(mini_html_content)
        
        print(f"         -> [成功存檔] {filename} (已完成 Token 輕量化壓縮)")
