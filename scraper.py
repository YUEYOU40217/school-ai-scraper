import json
import os
import re
import utils
from datetime import datetime, timedelta, timezone
from google import genai
from urllib.parse import urljoin

MAX_LIMIT = 100 

def format_json_keywords(json_str):
    pattern = r'"keywords":\s*\[\s*([^\]]*?)\s*\]'
    def replace_func(match):
        items = match.group(1).split('\n')
        cleaned_items = [item.strip() for item in items if item.strip()]
        joined_items = "".join(cleaned_items).replace('","', '", "')
        return f'"keywords": [{joined_items}]'
    return re.sub(pattern, replace_func, json_str, flags=re.DOTALL)

def main():
    # 1. 讀取設定檔
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 💡 核心改版：指定整點檢查機制
    scheduled_hours = config.get("scheduled_hours", [])
    if scheduled_hours:
        # 強制將時間校正為台灣時間 (UTC+8)，避免 GitHub Action 雲端時差錯誤
        tz_taiwan = timezone(timedelta(hours=8))
        current_hour = datetime.now(tz_taiwan).hour
        
        if current_hour not in scheduled_hours:
            print(f"目前台灣時間為 {current_hour} 點，非設定的執行整點 {scheduled_hours}。直接中斷任務以節省資源。")
            return
        print(f"目前台灣時間為 {current_hour} 點，符合設定整點，開始執行爬蟲...")

    allowed_years = config.get("allowed_years", [2025, 2026])
    year_keywords = []
    for y in allowed_years:
        year_keywords.append(str(y))          
        year_keywords.append(str(y - 1911))   
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    all_sites_output = []

    # 2. 巡迴執行各網站
    for site in config.get("sites", []):
        target_url = site['url']
        site_name = site['name']
        
        print(f"智慧盲猜啟動，正在處理網站: {site_name}")
        
        source_name, all_links = utils.fetch_links_smart(target_url)
        
        if not all_links:
            print(f"警告：{site_name} 未能偵測到任何公告，跳過。")
            continue

        # 依照日期由新到遠排序
        all_links.sort(key=lambda x: x['date'], reverse=True)

        processed_data = []
        current_id = 1
        out_of_range_count = 0 

        for item in all_links[:MAX_LIMIT]:
            is_valid_year = any(k in item['row_text'] for k in year_keywords)

            if not is_valid_year:
                out_of_range_count += 1
                if out_of_range_count >= 3:
                    print(f"[{site_name}] 偵測到已進入舊年份資料區，停止該網站後續 AI 請求。")
                    break
                continue
            
            out_of_range_count = 0
            full_url = urljoin(target_url, item['href'])
            print(f"[{site_name}] 請 AI 萃取關鍵字 (ID {current_id}): {item['title']}")
            
            ai_res = utils.process_ai(item['title'], config['prompt_template'], client)
            
            record = {
                "id": current_id,
                "title": item['title'],
                "link": full_url,
                "keywords": ai_res.get("keywords", [])
            }
            processed_data.append(record)
            current_id += 1

        site_packet = {
            "source_name": source_name,
            "source_link": target_url,
            "data": processed_data
        }
        all_sites_output.append(site_packet)

    raw_json = json.dumps(all_sites_output, ensure_ascii=False, indent=2)
    final_json = format_json_keywords(raw_json)

    with open("announcements.json", "w", encoding="utf-8") as f:
        f.write(final_json)
        
    print("全部網站處理完畢！")

if __name__ == "__main__":
    main()
