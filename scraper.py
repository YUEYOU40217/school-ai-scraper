import json
import os
import re
import utils
from datetime import datetime, timedelta, timezone
from google import genai
from urllib.parse import urljoin

MAX_RAW_LIMIT = 100 
# 💡 每一次打包餵給 AI 的公告筆數 (設定 5 筆是最平衡、最不容易出錯的完美數量)
BATCH_SIZE = 5 

def format_json_keywords(json_str):
    pattern = r'"keywords":\s*\[\s*([^\]]*?)\s*\]'
    def replace_func(match):
        items = match.group(1).split('\n')
        cleaned_items = [item.strip() for item in items if item.strip()]
        joined_items = "".join(cleaned_items).replace('","', '", "')
        return f'"keywords": [{joined_items}]'
    return re.sub(pattern, replace_func, json_str, flags=re.DOTALL)

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
    all_sites_output = []

    for site in config.get("sites", []):
        target_url = site['url']
        site_name = site['name']
        
        print(f"智慧盲猜啟動，正在處理網站: {site_name}")
        source_name, all_links = utils.fetch_links_smart(target_url)
        
        if not all_links:
            print(f"警告：{site_name} 未能偵測到任何公告，跳過。")
            continue

        all_links.sort(key=lambda x: x['date'], reverse=True)

        # 💡 步驟 1：地端初篩，先收集這家網站所有符合年份的合法公告
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

        # 💡 步驟 2：開始進行「分批切片餵食 (Batching)」
        processed_data = []
        current_id = 1
        
        print(f"[{site_name}] 合格公告共 {len(valid_items)} 筆，開始進行每 {BATCH_SIZE} 筆分批打包解析...")
        
        for i in range(0, len(valid_items), BATCH_SIZE):
            # 切片切出當前的批次 (例如 0~5, 5~10...)
            batch = valid_items[i : i + BATCH_SIZE]
            batch_titles = [item['title'] for item in batch]
            
            print(f"[{site_name}] 正在發送批次請求 (當前打包共 {len(batch_titles)} 筆)...")
            # 把這一整批標題直接塞給 AI
            batch_ai_results = utils.process_ai_batch(batch_titles, config['prompt_template'], client)
            
            # 將 AI 回傳的批次結果與原公告資料進行對齊組合
            for idx, item in enumerate(batch):
                full_url = urljoin(target_url, item['href'])
                
                # 安全防護：確保 AI 回傳的數量夠用，如果不夠就塞保底失敗
                keywords = ["解析失敗"]
                if idx < len(batch_ai_results):
                    keywords = batch_ai_results[idx].get("keywords", ["解析失敗"])
                
                record = {
                    "id": current_id,
                    "title": item['title'],
                    "link": full_url,
                    "keywords": keywords
                }
                processed_data.append(record)
                current_id += 1

        if processed_data:
            site_packet = {
                "source_name": source_name,
                "source_link": target_url,
                "data": processed_data
            }
            all_sites_output.append(site_packet)

    # 存檔
    raw_json = json.dumps(all_sites_output, ensure_ascii=False, indent=2)
    final_json = format_json_keywords(raw_json)

    with open("announcements.json", "w", encoding="utf-8") as f:
        f.write(final_json)
        
    print("全部網站批次打包處理完畢！")

if __name__ == "__main__":
    main()
