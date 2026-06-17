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
    processed_urls = set()

    # 地毯式掃描所有連結標籤
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if not href:
            continue

        # 補全相對路徑為絕對路徑
        full_url = urljoin(target_url, href)
        
        # 排除非網頁連結與重複連結
        if not full_url.startswith("http") or full_url in processed_urls:
            continue

        title = clean_pure_text(anchor.get_text())
        
        # 過濾明顯屬於網站選單、導覽列的無效文字
        if len(title) < 4 or any(kw in title.lower() for kw in ["跳到", "首頁", "menu", "login", "english", "search", "交通"]):
            continue

        # 尋找日期：1. 先從標題字串找 2. 找不到則往上遞迴 5 層父節點容器尋找
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

        # 若仍無日期，則標記為 UNRESOLVED
        final_date = date_found if date_found else "UNRESOLVED"

        announcements.append({
            "title": title,
            "href": full_url,
            "date": final_date
        })
        processed_urls.add(full_url)

    return announcements

def main():
    print("啟動全量無損爬蟲更新管線...")
    scraped_data = start_scraping()
    
    # 建立符合 GitHub Actions 部署要求的 public 目錄
    output_folder = "public"
    os.makedirs(output_folder, exist_ok=True)
    
    output_file_path = os.path.join(output_folder, "data.json")
    
    payload = {
        "site_name": "正修科技大學公告監控",
        "total_records": len(scraped_data),
        "data": scraped_data
    }
    
    with open(output_file_path, "w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=4)
        
    print(f"任務完成。成功將 {len(scraped_data)} 筆全量數據寫入 {output_file_path}")

if __name__ == "__main__":
    main()
