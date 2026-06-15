import json
from DrissionPage import ChromiumPage, ChromiumOptions
from utils import extract_date, is_valid_announcement

def get_announcements():
    target_url = "https://www.csu.edu.tw/p/403-1000-13-1.php?Lang=zh-tw"
    
    # 初始化瀏覽器
    co = ChromiumOptions().auto_port()
    co.headless(True)
    page = ChromiumPage(co)
    
    try:
        print(f"正在前往: {target_url}")
        page.get(target_url)
        
        # 等待連結與關鍵元素載入 (最多等待 10 秒)
        page.wait.ele_loaded('tag:a', timeout=10)
        
        # 抓取所有連結
        all_links = page.eles('tag:a')
        
        results = []
        
        # 遍歷所有連結並進行篩選
        for link in all_links:
            title = link.text
            href = link.link
            
            # 1. 基礎過濾：去除導覽雜訊
            if not is_valid_announcement(title, href):
                continue
                
            # 2. 獲取該行文字 (包含日期)
            # 使用 parent 取得該行容器，確保能抓到日期文字
            row_text = link.parent(2).text
            date = extract_date(row_text)
            
            # 3. 強制過濾：只有「帶有日期」的才算公告
            if date:
                results.append({
                    "title": title,
                    "href": href,
                    "date": date
                })
        
        # 移除重複 (若有的話)
        unique_results = {item['href']: item for item in results}.values()
        return list(unique_results)

    except Exception as e:
        print(f"爬取過程發生錯誤: {e}")
        return []
    finally:
        page.quit()

def main():
    data = get_announcements()
    
    # 輸出檢查
    print(f"成功抓取到 {len(data)} 筆公告。")
    
    # 寫入 JSON 供你除錯與後續 AI 處理
    with open("raw_scraped_data.json", 'w', encoding='utf-8') as f:
        json.dump({"announcements": data}, f, ensure_ascii=False, indent=4)
        
    print("資料已儲存至 raw_scraped_data.json，請檢查數量是否為 15 筆。")

if __name__ == "__main__":
    main()
