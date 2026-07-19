import requests
import time

# 請替換成你實際抓取的學務處公告列表 URL 結構
# 假設網址結尾是用 page=1, page=2 來換頁
base_url = "https://www.csu.edu.tw/bulletin?page=" 

headers = {
    # 加上 User-Agent 避免被阻擋
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 設定爬取 1 到 3 頁
for page in range(1, 4):
    url = f"{base_url}{page}"
    print(f"正在抓取第 {page} 頁列表...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 取得完整的三頁 HTML 原始碼
        raw_html = response.text
        
        # 直接將完整的 HTML 寫入檔案，方便你後續檢查 DOM 結構
        file_name = f"list_page_{page}.html"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(raw_html)
        print(f"已儲存: {file_name}")

        # =====================================================================
        # 以下為原本「點進去找日期與整理資料」的邏輯，先全部註解掉
        # =====================================================================
        
        # soup = BeautifulSoup(raw_html, "html.parser")
        # articles = soup.find_all("div", class_="announcement-item") # 假設的 class
        # 
        # for article in articles:
        #     # 1. 抓取標題與連結
        #     title = article.find("a").text
        #     inner_url = article.find("a")["href"]
        #     
        #     # 2. 點進內頁找日期 (原本會觸發防呆機制的源頭)
        #     inner_response = requests.get(inner_url, headers=headers)
        #     inner_soup = BeautifulSoup(inner_response.text, "html.parser")
        #     
        #     # 策略 A 與 策略 B 的日期尋找邏輯
        #     date = extract_date_from_inner_page(inner_soup) 
        #     
        #     # 3. 整理資料
        #     data_list.append({
        #         "title": title,
        #         "date": date,
        #         "url": inner_url
        #     })
        
        # =====================================================================

        # 避免請求過於頻繁，設定 1 秒延遲
        time.sleep(1)

    except requests.exceptions.RequestException as e:
        print(f"第 {page} 頁抓取失敗: {e}")

print("前 3 頁 HTML 原始碼抓取完畢！")
