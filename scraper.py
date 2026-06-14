import json
import os
import re
import uuid
import utils
from datetime import datetime
from google import genai
from urllib.parse import urljoin

MAX_RAW_LIMIT = 1000 
BATCH_SIZE = 20 

def format_json_keywords(json_str):
    """壓縮關鍵字陣列排版為單行，使 JSON 檔更易於閱讀"""
    pattern = r'"keywords":\s*\[\s*([^\]]*?)\s*\]'
    def replace_func(match):
        items = match.group(1).split('\n')
        cleaned_items = [item.strip() for item in items if item.strip()]
        joined_items = "".join(cleaned_items).replace('","', '", "')
        return f'"keywords": [{joined_items}]'
    return re.sub(pattern, replace_func, json_str, flags=re.DOTALL)

def clean_and_parse_date(date_str):
    """將西元格式字串解析為 datetime 物件，供排序使用"""
    try:
        nums = [int(s) for s in re.findall(r'\d+', date_str)]
        if len(nums) < 3:
            return datetime(1970, 1, 1)
        return datetime(nums[0], nums[1], nums[2])
    except:
        return datetime(1970, 1, 1)

def main():
    # 讀取設定檔
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    print("開始執行爬蟲任務。")

    history_site_backup = {} 
    existing_uuid_map = {}
    history_file = "announcements.json"
    
    # 載入歷史資料以維持 UUID 的一致性，並建立斷線備援還原點
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                for site_info in history_data:
                    if "source_link" in site_info:
                        history_site_backup[site_info["source_link"]] = site_info
                        
                    for item in site_info.get("data", []):
                        if "link" in item and "uuid" in item:
                            existing_uuid_map[item["link"]] = item["uuid"]
            print(f"成功載入歷史資料，共記憶了 {len(existing_uuid_map)} 筆現有的 UUID 對照。")
        except Exception as e:
            print(f"讀取歷史 json 失敗或格式不符，將視為全新資料處理。錯誤原因: {e}")

    # 初始化 Google GenAI 用戶端
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    raw_scraped_log = []       # 用於儲存完全未過濾的原始爬取日誌
    all_extracted_records = []  # 用於儲存經 AI 驗證年份過關的公告

    for site in config.get("sites", []):
        target_url = site['url']
        site_name = site['name']
        
        print(f"啟動網站處理: {site_name}")
        source_name, all_links = utils.fetch_links_smart(target_url)
        
        if not all_links:
            print(f"警告：{site_name} 未能偵測到任何公告，跳過本次抓取。")
            continue

        # 1. 毫無過濾地將原始爬取資訊寫入日誌物件
        raw_scraped_log.append({
            "site_name": site_name,
            "url": target_url,
            "total_raw_found": len(all_links),
            "links": all_links[:MAX_RAW_LIMIT]
        })

        valid_items = all_links[:MAX_RAW_LIMIT]

        print(f"[{site_name}] 原始抓取共 {len(valid_items)} 筆，開始進行每 {BATCH_SIZE} 筆分批打包送給 AI 解析與年份過濾。")
        
        # 2. 將含有標題與上下文 row_text 的資料批次打包發給 Gemini AI
        for i in range(0, len(valid_items), BATCH_SIZE):
            batch = valid_items[i : i + BATCH_SIZE]
            
            # 包裹上下文資訊提供 AI 充足的推導日期線索
            batch_inputs_for_ai = [f"標題: {item['title']} | 周邊文字: {item['row_text']}" for item in batch]
            
            print(f"[{site_name}] 正在發送批次請求 (當前打包共 {len(batch_inputs_for_ai)} 筆)。")
            batch_ai_results = utils.process_ai_batch(batch_inputs_for_ai, config['prompt_template'], client)
            
            for idx, item in enumerate(batch):
                full_url = urljoin(target_url, item['href'])
                
                # 讀取 AI 判定的結果
                ai_res = batch_ai_results[idx] if idx < len(batch_ai_results) else {}
                is_allowed = ai_res.get("is_allowed_year", True) 
                extracted_date = ai_res.get("extracted_date", "1970-01-01")
                keywords = ai_res.get("keywords", ["解析失敗"])
                
                # 如果 AI 判定該公告不屬於允許年份（如過往舊公告），在此直接過濾排除
                if not is_allowed:
                    continue
                
                all_extracted_records.append({
                    "source_name": source_name,
                    "source_link": target_url, 
                    "title": item['title'],
                    "link": full_url,
                    "keywords": keywords,
                    "raw_date": item['date'],
                    "extracted_date_str": extracted_date,
                    "parsed_datetime": clean_and_parse_date(extracted_date)
                })

    # 3. 將最原始無修剪的爬蟲內容寫入 raw_scraped.json，方便對照與 Debug
    with open("raw_scraped.json", "w", encoding="utf-8") as rf:
        json.dump(raw_scraped_log, rf, ensure_ascii=False, indent=2)
    print("已成功將原始爬取內容寫入 raw_scraped.json 供檢查。")

    # 4. 依照 AI 標準化的西元日期進行由新到舊排序
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

    # 🛡️ 備援機制：如果某網站本次連線或抓取完全失敗，從歷史記錄還原防止最終檔案被清空
    for site in config.get("sites", []):
        target_url = site['url']
        if target_url not in site_data_map:
            if target_url in history_site_backup:
                print(f"🛡️  [安全機制啟動] 偵測到 {site['name']} 本次連線或抓取失敗。已成功從歷史紀錄中還原舊有公告！")
                site_data_map[target_url] = history_site_backup[target_url]
            else:
                print(f"ℹ️  {site['name']} 本次無新資料且歷史無紀錄，略過。")

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

    # 輸出最終精煉與 AI 年份篩選後的公告檔
    with open("announcements.json", "w", encoding="utf-8") as f:
        f.write(final_json)
        
    print("全部網站處理完畢，已成功更新資料並寫入 announcements.json。")

if __name__ == "__main__":
    main()
