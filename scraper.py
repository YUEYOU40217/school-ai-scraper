import json
import os
import utils
from google import genai
from urllib.parse import urljoin

BATCH_SIZE = 15 

def main():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    target_url = config['urls'][0]
    print(f"鎖定目標網址: {target_url}")
    
    selector_cfg = config.get('selector_config', {})
    row_selector = selector_cfg.get('row_selector', '.mtitle')
    link_selector = selector_cfg.get('link_selector', 'a')
    
    all_links = utils.fetch_links(target_url, row_selector, link_selector)
    
    if not all_links:
        print("警告：抓到的連結數量為 0！")
        return

    allowed_years = config.get("allowed_years", [2026])
    year_keywords = []
    for y in allowed_years:
        year_keywords.append(str(y))          
        year_keywords.append(str(y - 1911))   
    
    print(f"年份範圍過濾：只處理包含 {year_keywords} 的公告條目")

    progress = {"index": 0} 
    idx = progress["index"]
    batch = all_links[idx : idx + BATCH_SIZE]

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    final_data = []
    if os.path.exists("announcements.json"):
        with open("announcements.json", "r", encoding="utf-8") as f:
            try: 
                final_data = json.load(f)
            except: 
                final_data = []

    processed_count = 0

    for item in batch:
        if not any(k in item['row_text'] for k in year_keywords):
            print(f"非設定年份範圍，跳過: {item['title']}")
            continue

        full_url = urljoin(target_url, item['href'])
        print(f"正在請 AI 萃取關鍵字: {item['title']}")
        
        ai_res = utils.process_ai(item['title'], config['prompt_template'], client)
        
        record = {
            "title": item['title'],
            "link": full_url,
            "keywords": ai_res.get("keywords", [])
        }
        final_data.append(record)
        processed_count += 1

    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"成功處理 {processed_count} 筆符合年份範圍的公告關鍵字！")

if __name__ == "__main__":
    main()
