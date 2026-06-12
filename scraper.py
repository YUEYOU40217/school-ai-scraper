import json, os, utils
import google.generativeai as genai
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

# 設定
BATCH_SIZE = 10 

def main():
    # 讀取 config
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 時間檢查
    taiwan_tz = timezone(timedelta(hours=8))
    if datetime.now(taiwan_tz).hour not in config.get("active_hours", []):
        return

    # 讀取進度
    if os.path.exists("progress.json"):
        with open("progress.json", "r") as f: progress = json.load(f)
    else: progress = {"index": 0}

    # 獲取連結
    all_links = utils.fetch_links(config['urls'][0], config['selector_config']['row_selector'])
    
    # 分批處理
    idx = progress["index"]
    batch = all_links[idx : idx + BATCH_SIZE]
    
    if not batch:
        print("所有公告已處理完畢！")
        return

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash-lite')
    
    final_data = []
    for item in batch:
        print(f"正在處理: {item['title']}")
        # 這裡省略內頁抓取邏輯...
        ai_res = utils.process_ai(item['title'], config['prompt_template'], model)
        ai_res['link'] = urljoin(config['urls'][0], item['href'])
        final_data.append(ai_res)

    # 儲存結果與更新進度
    with open("announcements.json", "a", encoding="utf-8") as f:
        for entry in final_data: f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    progress["index"] += BATCH_SIZE
    with open("progress.json", "w") as f: json.dump(progress, f)
    print(f"本批次處理完成，下一批次從 {progress['index']} 開始。")

if __name__ == "__main__":
    main()
