import os
import json
from bs4 import BeautifulSoup

def run(site_output_dir, fetch_content):
    os.makedirs(site_output_dir, exist_ok=True)
    
    category = "教務處"
    
    # 只需要抓第一頁，因為所有資料都在這一頁的 HTML 裡
    target_url = "https://acad.nkust.edu.tw/p/403-1063-2072-1.php?Lang=zh-tw"
    print(f"      [{category}] 開始抓取: {target_url}")
    
    html_content = fetch_content(target_url)
    if not html_content:
        print(f"         -> [抓取失敗] 無法取得內容")
        return
        
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 找到公告列表的表格 (根據 HTML，表格 class 為 listTB table)
    table = soup.find("table", class_="listTB table")
    if not table:
        print("         -> [解析失敗] 找不到公告表格")
        return
        
    # 抓取 tbody 內所有的 tr (每一列就是一筆公告)
    rows = table.find("tbody").find_all("tr")
    print(f"         -> 成功在第一頁找到 {len(rows)} 筆公告！")
    
    results = []
    
    # 開始解析每一筆公告
    for row in rows:
        # 1. 解析日期
        date_td = row.find("td", {"data-th": "日期"})
        date_str = date_td.find("div", class_="d-txt").get_text(strip=True) if date_td else ""
        
        # 2. 解析標題與連結
        title_td = row.find("td", {"data-th": "標題"})
        if title_td:
            a_tag = title_td.find("a")
            if a_tag:
                title = a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                
                # 清理標題中多餘的換行或空白
                title = " ".join(title.split())
                
                # 3. 解析發布單位
                unit_td = row.find("td", {"data-th": "資料建立者"})
                unit = unit_td.find("div", class_="d-txt").get_text(strip=True) if unit_td else ""
                
                results.append({
                    "date": date_str,
                    "title": title,
                    "link": link,
                    "unit": unit
                })
    
    # 將結果儲存成 JSON 檔案
    if results:
        output_file = os.path.join(site_output_dir, f"{category}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"         -> [成功存檔] 已將 {len(results)} 筆資料儲存至 {output_file}")
    else:
        print("         -> [警告] 沒有抓取到任何資料，未產生檔案。")
