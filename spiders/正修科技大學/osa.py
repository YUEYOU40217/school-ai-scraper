import requests
from bs4 import BeautifulSoup
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 準備要輸出的檔案
output_filename = "csu_announcements_ai_format.html"

with open(output_filename, "w", encoding="utf-8") as f:
    # 針對第 1 到第 3 頁進行迴圈爬取
    for page in range(1, 4):
        list_url = f"https://osa.csu.edu.tw/p/403-1069-195-{page}.php?Lang=zh-tw"
        print(f"正在抓取第 {page} 頁列表...")
        
        try:
            response = requests.get(list_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 找到清單中所有的公告區塊
            articles = soup.find_all("div", class_="mtitle")
            
            for article in articles:
                a_tag = article.find("a")
                if not a_tag:
                    continue
                    
                title = a_tag.text.strip()
                link = a_tag.get("href")
                
                # 初始化預設值
                date = "N/A"
                
                # 處理相對路徑
                if link.startswith("/"):
                    link = "https://osa.csu.edu.tw" + link
                
                # 過濾器：判斷是否為學務處內容 (osa.csu.edu.tw)
                if "osa.csu.edu.tw" in link:
                    try:
                        inner_resp = requests.get(link, headers=headers, timeout=10)
                        inner_soup = BeautifulSoup(inner_resp.text, "html.parser")
                        
                        # 在內頁尋找日期
                        date_tag = inner_soup.find("i", class_="mdate")
                        if date_tag:
                            date = date_tag.text.strip()
                            
                    except Exception as e:
                        print(f"    [連線內頁失敗] {link}")
                    
                    # 點擊內頁後設定延遲，避免伺服器阻擋
                    time.sleep(0.5)
                else:
                    print(f"    [跳過外部連結] {title}")
                
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
                # 寫入檔案
                f.write(html_block + "\n")
                
        except Exception as e:
            print(f"第 {page} 頁抓取失敗: {e}")
            
        # 換下一頁前設定延遲
        time.sleep(1)

print(f"\n抓取完畢！已將格式化內容儲存於: {output_filename}")
