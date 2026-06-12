import json, os, utils
import google.generativeai as genai
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

BATCH_SIZE = 10 # 每次處理 10 筆，避免過載

def main():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 時間檢查
    taiwan_tz = timezone(timedelta(hours=8))
    if datetime.now(taiwan_tz).hour not in config.get("active_hours", []):
        print("非執行時段。")
        return

    # 1. 讀取進度 (若無則從0開始)
    progress_file = "progress.json"
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f: progress = json.load(f)
    else: progress = {"index": 0}

    # 2. 自動導航至公告頁面
    target_url = utils.find_announcement_page(config['urls'][0])
    all_links = utils.fetch_links(target_url, config['selector_config']['row_selector'])
    
    # 3. 分批處理
    idx = progress["index"]
    batch = all_links[idx : idx + BATCH_SIZE]
    
    if not batch:
        print("所有公告已處理完畢！")
        return

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash-lite')
    
    # 讀取舊資料以便追加
    final_data = []
    if os.path.exists("announcements.json"):
        with open("announcements.json", "r", encoding="utf-8") as f:
            try: final_data = json.load(f)
            except: final_data = []

    for item in batch:
        print(f"正在處理: {item['title']}")
        # 這裡簡單處理內頁連結的摘要，若你需要內頁內容可擴充 utils
        ai_res = utils.process_ai(item['title'], config['prompt_template'], model)
        ai_res['link'] = urljoin(target_url, item['href'])
        final_data.append(ai_res)

    # 4. 存檔與更新進度
    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    progress["index"] += BATCH_SIZE
    with open(progress_file, "w") as f: json.dump(progress, f)
    print(f"成功處理 {len(batch)} 筆，進度更新至 {progress['index']}")

if __name__ == "__main__":
    main()
