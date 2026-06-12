import json
import os
import re
import utils
from datetime import datetime, timedelta, timezone
from google import genai
from urllib.parse import urljoin

MAX_RAW_LIMIT = 100 
BATCH_SIZE = 10 

def format_json_keywords(json_str):
    pattern = r'"keywords":\s*\[\s*([^\]]*?)\s*\]'
    def replace_func(match):
        items = match.group(1).split('\n')
        cleaned_items = [item.strip() for item in items if item.strip()]
        joined_items = "".join(cleaned_items).replace('","', '", "')
        return f'"keywords": [{joined_items}]'
    return re.sub(pattern, replace_func, json_str, flags=re.DOTALL)

def clean_and_parse_date(date_str):
    """💡 核心優化：將各種奇形怪狀的日期（民國、斜線、橫線）統一轉換為可以正確排序的 datetime 物件"""
    try:
        # 取出純數字部分
        nums = [int(s) for s in re.findall(r'\d+', date_str)]
        if len(nums) < 3:
            return datetime(1970, 1, 1) # 格式不對的丟到最後面
        
        year, month, day = nums[0], nums[1], nums[2]
        # 如果是民國年 (小於 200)
        if year < 200:
            year += 1911
            
        return datetime(year, month, day)
    except:
        return datetime(1970, 1, 1)

def main():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    scheduled_hours = config.get("scheduled_hours", [])
    if scheduled_hours:
        tz_taiwan = timezone(timedelta(hours=8))
        current_hour = datetime.now(tz_taiwan).hour
        if current_hour not in scheduled_hours:
            print(f"目前台灣時間為 {current_hour} 點，非設定的執行整點 {scheduled_hours}。")
            return

    allowed_years = config.get("allowed_years", [2025, 2026])
    year_keywords = []
    for y in allowed_years:
        year_keywords.append(str(y))          
        year_keywords.append(str(y - 1911))   
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # 💡 這裡改成用一個扁平的清單，把所有網站抓到的公告先「借放」在一起
    all_extracted_records = []

    for site in config.get("sites", []):
        target_url = site['url']
        site_name = site['name']
        
        print(f"智慧盲猜啟動，正在處理網站: {site_name}")
        source_name, all_links = utils.fetch_links_smart(target_url)
        
        if not all_links:
            print(f"警告：{site_name} 未能偵測到任何公告，跳過。")
            continue

        valid_items = []
        out_of_range_count = 0 

        for item in all_links[:MAX_RAW_LIMIT]:
            is_valid_year = any(k in item['row_text'] for k in year_keywords)

            if not is_valid_year:
                out_of_range_count += 1
                if out_of_range_count >= 3:
                    print(f"[{site_name}] 偵測到已進入舊年份資料區，停止該網站後續處理。")
                    break
                continue
            
            out_of_range_count = 0
            valid_items.append(item)

        print(f"[{site_name}] 合格公告共 {len(valid_items)} 筆，開始進行每 {BATCH_SIZE} 筆分批打包解析...")
        
        for i in range(0, len(valid_items), BATCH_SIZE):
            batch = valid_items[i : i + BATCH_SIZE]
            batch_titles = [item['title'] for item in batch]
            
            print(f"[{site_name}] 正在發送批次請求 (當前打包共 {len(batch_titles)} 筆)...")
            batch_ai_results = utils.process_ai_batch(batch_titles, config['prompt_template'], client)
            
            for idx, item in enumerate(batch):
                full_url = urljoin(target_url, item['href'])
                
                keywords = ["解析失敗"]
                if idx < len(batch_ai_results):
                    keywords = batch_ai_results[idx].get("keywords", ["解析失敗"])
                
                # 先把資料塞進全域大池子裡，並且記錄網站來源
                all_extracted_records.append({
                    "source_name": source_name,
                    "source_link": target_url,
                    "title": item['title'],
                    "link": full_url,
                    "keywords": keywords,
                    "raw_date": item['date'], # 留下原始日期文字
                    "parsed_datetime": clean_and_parse_date(item['date']) # 轉化為可用於精準排序的物件
                })

    # 💡 終極全域排序：不分學校，把池子裡所有的公告，按照日期從最新到最舊（降序）大洗牌！
    all_extracted_records.sort(key=lambda x: x['parsed_datetime'], reverse=True)

    # 💡 重新包裝成你原本習慣的按學校分類的結構，但「順序已經完全依照日期排好」
    final_output = []
    site_data_map = {}

    current_id = 1
    for rec in all_extracted_records:
        src_url = rec['source_link']
        if src_url not in site_data_map:
            site_data_map[src_url] = {
                "source_name": rec['source_name'],
                "source_link": src_url,
                "data": []
            }
        
        # 建立每一筆公告的最終格式
        site_data_map[src_url]["data"].append({
            "id": current_id, # 💡 這裡的 ID 會完美對應「全網最新到最舊」的順序
            "title": rec['title'],
            "link": rec['link'],
            "keywords": rec['keywords']
        })
        current_id += 1

    final_output = list(site_data_map.values())

    # 存檔
    raw_json = json.dumps(final_output, ensure_ascii=False, indent=2)
    final_json = format_json_keywords(raw_json)

    with open("announcements.json", "w", encoding="utf-8") as f:
        f.write(final_json)
        
    print("全部網站處理完畢，且已完成全域最新日期排序！")

if __name__ == "__main__":
    main()
