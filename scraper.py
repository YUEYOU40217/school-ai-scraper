import os
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils import fetch_page_html, clean_pure_text, match_date_format

def start_scraping():
    target_url = "https://www.csu.edu.tw/p/403-1000-13-1.php?Lang=zh-tw"
    html_content = fetch_page_html(target_url)
    
    if not html_content:
        print("無法載入目標網頁，終止執行。")
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    announcements = []

    # 抓取頁面中「所有」的 <a> 標籤，不放過任何一個
    all_anchors = soup.find_all("a")
    print(f"網頁偵測完成，共發現 {len(all_anchors)} 個原始連結項目。開始全量封裝...")

    for index, anchor in enumerate(all_anchors, start=1):
        href = anchor.get("href")
        title = clean_pure_text(anchor.get_text())
        
        # 即使沒有網址或沒有文字，也保留這筆資料（確保無損）
        full_url = urljoin(target_url, href) if href else "NO_HREF"

        # 向上追溯 5 層尋找該區塊的日期
        date_found = match_date_format(title)
        if not date_found:
            parent_node = anchor
            for _ in range(5):
                parent_node = parent_node.parent
                if not parent_node:
                    break
                container_text = parent_node.get_text(separator=" ")
                date_found = match_date_format(container_text)
                if date_found:
                    break

        final_date = date_found if date_found else "NO_DATE"

        # 毫無保留，全部打包
        announcements.append({
            "index": index,
            "title": title if title else "EMPTY_TEXT",
            "href": full_url,
            "date": final_date
        })

    return announcements

def main():
    print("啟動【零篩選・全量網頁內容抓取】管線...")
    scraped_data = start_scraping()
    
    # 建立符合 GitHub Actions 部署要求的 public 目錄
    output_folder = "public"
    os.makedirs(output_folder, exist_ok=True)
    
    output_file_path = os.path.join(output_folder, "data.json")
    
    payload = {
        "site_name": "正修科技大學全網頁原始連結備份",
        "total_records": len(scraped_data),
        "data": scraped_data
    }
    
    with open(output_file_path, "w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=4)
        
    print(f"任務完成。已將 {len(scraped_data)} 筆最原始的網頁資料寫入 {output_file_path}")

if __name__ == "__main__":
    main()
