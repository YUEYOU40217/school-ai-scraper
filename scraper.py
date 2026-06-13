import json
import os
import re
import uuid
import utils
from datetime import datetime
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
    try:
        nums = [int(s) for s in re.findall(r'\d+', date_str)]
        if len(nums) < 3:
            return datetime(1970, 1, 1)
        year, month, day = nums[0], nums[1], nums[2]
        if year < 200:
            year += 1911
        return datetime(year, month, day)
    except:
        return datetime(1970, 1, 1)

def main():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    print("開始執行爬蟲任務。")

    existing_uuid_map = {}
    history_file = "announcements.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                for site_info in history_data:
                    for item in site_info.get("data", []):
                        if "link" in item and "uuid" in item:
                            existing_uuid_map[item["link"]] = item["uuid"]
            print(f"成功載入歷史資料，共記憶了 {len(existing_uuid_map)} 筆現有的 UUID 對照。")
        except Exception as e:
            print(f"讀取歷史 json 失敗或格式不符，將視為全新資料處理。錯誤原因: {e}")

    allowed_years = config.get("allowed_years", [2025, 2026])
    year_keywords = []
    for y in allowed_years:
        year_keywords.append(str(y))          
        year_keywords.append(str(y - 1911))   
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    all_extracted_records = []

    for site in config.get("sites", []):
        target_url = site['url']
        site_name = site['name']
        
        print(f"啟動網站處理: {site_name}")
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

        print(f"[{site_name}] 合格公告共 {len(valid_items)} 筆，開始進行每 {BATCH_SIZE} 筆分批打包解析。")
        
        for i in range(0, len(valid_items), BATCH_SIZE):
            batch = valid_items[i : i + BATCH_SIZE]
            batch_titles = [item['title'] for item in batch]
            
            print(f"[{site_name}] 正在發送批次請求 (當前打包共 {len(batch_titles)} 筆)。")
            batch_ai_results = utils.process_ai_batch(batch_titles, config['prompt_template'], client)
            
            for idx, item in enumerate(batch):
                full_url = urljoin(target_url, item['href'])
                keywords = ["解析失敗"]
                if idx < len(batch_ai_results):
                    keywords = batch_ai_results[idx].get("keywords", ["解析失敗"])
                
                all_extracted_records.append({
                    "source_name": source_name,
                    "source_link": target_url,
                    "title": item['title'],
                    "link": full_url,
                    "keywords": keywords,
                    "raw_date": item['date'],
                    "parsed_datetime": clean_and_parse_date(item['date'])
                })

    all_extracted_records.sort(key=lambda x: x['parsed_datetime'], reverse=True)

    site_data_map = {}
    
    for rec in all_extracted_records:
        src_url = rec['source_link']
        if src_url not in site_data_map:
            site_data_map[src_url] = {
                "source_name": rec['source_name'],
                "source_link": src_url,
                "data": []
            }
        
        target_link = rec['link']
        if target_link in existing_uuid_map:
            assigned_uuid = existing_uuid_map[target_link]
        else:
            assigned_uuid = str(uuid.uuid4())
            existing_uuid_map[target_link] = assigned_uuid
        
        site_data_map[src_url]["data"].append({
            "uuid": assigned_uuid,
            "title": rec['title'],
            "link": target_link,
            "keywords": rec['keywords']
        })

    final_output = []
    
    for site_info in site_data_map.values():
        final_output.append({
            "source_name": site_info["source_name"],
            "source_link": site_info["source_link"],
            "total_count": len(site_info["data"]),
            "data": site_info["data"]
        })

    raw_json = json.dumps(final_output, ensure_ascii=False, indent=2)
    final_json = format_json_keywords(raw_json)

    with open("announcements.json", "w", encoding="utf-8") as f:
        f.write(final_json)
        
    print("全部網站處理完畢，已成功更新資料並寫入 announcements.json。")

if __name__ == "__main__":
    main()
