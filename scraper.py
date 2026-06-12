import json, os, utils
from google import genai
from datetime import datetime
from urllib.parse import urljoin

BATCH_SIZE = 10 

def main():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    target_url = config['urls'][0]
    print(f"🎯 鎖定目標網址: {target_url}")
    
    selector_cfg = config.get('selector_config', {})
    row_selector = selector_cfg.get('row_selector', '.mtitle')
    link_selector = selector_cfg.get('link_selector', 'a')
    
    all_links = utils.fetch_links(target_url, row_selector, link_selector)
    
    if not all_links:
        print("⚠️ 警告：抓到的連結數量為 0！")
        return

    # ⏳ 計算當前年份 (西元與民國)
    current_year = datetime.now().year
    roc_year = current_year - 1911
    year_keywords = [str(current_year), str(roc_year)]
    print(f"📅 啟動年份過濾器：只處理標題包含 {year_keywords} 的公告")

    progress = {"index": 0} 
    idx = progress["index"]
    batch = all_links[idx : idx + BATCH_SIZE]

    # 初始化新版 Gemini Client
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    final_data = []
    if os.path.exists("announcements.json"):
        with open("announcements.json", "r", encoding="utf-8") as f:
            try: final_data = json.load(f)
            except: final_data = []

    processed_count = 0

    for item in batch:
        # 🛡️ 關鍵字過濾：如果標題沒有當年的數字，直接跳過
        if not any(k in item['title'] for k in year_keywords):
            print(f"⏩ 非當年公告，跳過: {item['title']}")
            continue

        full_url = urljoin(target_url, item['href'])
        print(f"🤖 正在請 AI 處理: {item['title']} -> {full_url}")
        
        ai_res = utils.process_ai(full_url, config['prompt_template'], client)
        
        record = {
            "title": item['title'],
            "link": full_url,
            "summary": ai_res.get("summary", "無摘要")
        }
        final_data.append(record)
        processed_count += 1

    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 成功處理 {processed_count} 筆符合當年的新公告！")

if __name__ == "__main__":
    main()
