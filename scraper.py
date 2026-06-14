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

    print("開始執行全自動攻頂爬蟲任務。")

    history_site_backup = {} 
    existing_uuid_map = {}
    history_file = "announcements.json"
    
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
            print(f"讀取歷史 json 失敗，將視為全新資料處理。錯誤原因: {e}")

    allowed_years = config.get("allowed_years", [2025, 2026])
    allowed_years_str = ", ".join(map(str, allowed_years))
    
    year_keywords = []
    for y in allowed_years:
        year_keywords.append(str(y))          
        year_keywords.append(str(y - 1911))   
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    all_extracted_records = []

    for site in config.get("sites", []):
        base_url = site['url']
        site_name = site['name']
        max_pages = site.get("max_pages", 1)
        url_template = site.get("url_template", None)
        
        print(f"\n🚀 處理網站: {site_name}")
        
        combined_links = []
        final_source_name = "未命名網頁"
        target_page_urls = [base_url]

        # 1. 換頁網址決策核心
        if url_template:
            # 如果 config 有寫死換頁公式，就用公式產生
            target_page_urls = [url_template.replace("{page}", str(p)) for p in range(1, max_pages + 1)]
            print(f"  [模式A] 使用指定公式產生了 {len(target_page_urls)} 個分頁網址。")
        else:
            # 如果 config 沒寫公式，啟動「黑科技」：先抓第一頁，讓程式自動從 HTML 去撈出後面分頁
            print(f"  [模式B] 未指定公式，啟動 AI 級智慧尋頁探測...")
            first_name, first_links, first_soup = utils.fetch_links_smart(base_url)
            if first_soup:
                target_page_urls = utils.find_next_page_urls(first_soup, base_url, max_pages=max_pages)
            print(f"  [探測結果] 成功自動通靈出分頁網址共 {len(target_page_urls)} 頁：{target_page_urls}")

        # 2. 執行跨頁撈取
        seen_titles_or_urls = set()
        for idx, page_url in enumerate(target_page_urls):
            print(f"  正在抓取第 {idx+1} 頁: {page_url}")
            source_name, page_links, _ = utils.fetch_links_smart(page_url)
            
            if not page_links or source_name == "抓取失敗":
                continue
                
            final_source_name = source_name
            
            # 過濾重覆抓到的東西
            for lk in page_links:
                unique_key = lk["title"] + lk["href"]
                if unique_key not in seen_titles_or_urls:
                    combined_links.append(lk)
                    seen_titles_or_urls.add(unique_key)
        
        if not combined_links:
            print(f"  警告：{site_name} 所有分頁皆未偵測到任何公告。")
            continue

        # 3. 跨頁大名單年份阻斷
        valid_items = []
        out_of_range_count = 0 

        for item in combined_links[:MAX_RAW_LIMIT]:
            is_valid_year = any(k in item['row_text'] for k in year_keywords)

            if not is_valid_year:
                out_of_range_count += 1
                if out_of_range_count >= 3:
                    print(f"  [{site_name}] 進入舊年份歷史資料區，啟動安全阻斷機制。")
                    break
                continue
            
            out_of_range_count = 0
            valid_items.append(item)

        print(f"  [{site_name}] 跨頁合格公告共 {len(valid_items)} 筆，開始進行每 {BATCH_SIZE} 筆分批打包解析。")
        
        # 4. Gemini AI 解析防線
        for i in range(0, len(valid_items), BATCH_SIZE):
            batch = valid_items[i : i + BATCH_SIZE]
            batch_titles = [item['title'] for item in batch]
            
            batch_ai_results = utils.process_ai_batch(batch_titles, config['prompt_template'], client, allowed_years_str)
            
            for idx, item in enumerate(batch):
                full_url = urljoin(base_url, item['href'])
                keywords = ["解析失敗"]
                is_valid_announcement = True
                
                if idx < len(batch_ai_results):
                    ai_res = batch_ai_results[idx]
                    keywords = ai_res.get("keywords", ["解析失敗"])
                    if "is_valid" in ai_res and ai_res["is_valid"] is False:
                        is_valid_announcement = False
                
                if not is_valid_announcement:
                    continue
                
                all_extracted_records.append({
                    "source_name": final_source_name,
                    "source_link": base_url, 
                    "title": item['title'],
                    "link": full_url,
                    "keywords": keywords,
                    "raw_date": item['date'],
                    "parsed_datetime": clean_and_parse_date(item['date'])
                })

    # 5. 全網站跨校大排序與 UUID 記憶體維護
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

    # 6. 安全備份還原
    for site in config.get("sites", []):
        target_url = site['url']
        if target_url not in site_data_map:
            if target_url in history_site_backup:
                print(f"🛡️  [安全機制] {site['name']} 本次抓取異常，已從歷史紀錄中完整還原，防空檔保護成功！")
                site_data_map[target_url] = history_site_backup[target_url]

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
        
    print("\n🎉 狂賀！全自動跨頁大數據爬蟲任務圓滿完成，資料已成功存檔。")

if __name__ == "__main__":
    main()
