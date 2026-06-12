import json, os, utils
import google.generativeai as genai
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

BATCH_SIZE = 10 

def main():
    # 讀取設定檔
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 檢查是否在執行時段
    taiwan_tz = timezone(timedelta(hours=8))
    current_hour = datetime.now(taiwan_tz).hour
    if current_hour not in config.get("active_hours", []):
        print(f"當前時間為 {current_hour} 點，非執行時段。")
        return

    # 1. 讀取進度檔案
    progress_file = "progress.json"
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f: progress = json.load(f)
    else: progress = {"index": 0}

    # 2. 自動導航與清單抓取
    target_url = utils.find_announcement_page(config['urls'][0])
    
    # 從 config 安全讀取選擇器
    selector_cfg = config.get('selector_config', {})
    row_selector = selector_cfg.get('row_selector', 'tr')
    link_selector = selector_cfg.get('link_selector', 'a')
    
    all_links = utils.fetch_links(target_url, row_selector, link_selector)
    
    # 3. 分批截取處理
    idx = progress["index"]
    batch = all_links[idx : idx + BATCH_SIZE]
    
    if not batch:
        print("🎉 所有公告已處理完畢！")
        return

    # 初始化 Gemini (建議使用穩定且官方推薦的 'gemini-1.5-flash')
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 讀取現有歷史歷史資料
    final_data = []
    if os.path.exists("announcements.json"):
        with open("announcements.json", "r", encoding="utf-8") as f:
            try: final_data = json.load(f)
            except: final_data = []

    # 逐筆處理目前的 Batch
    for item in batch:
        full_url = urljoin(target_url, item['href'])
        print(f" 正在處理: {item['title']} -> {full_url}")
        
        # 呼叫 AI 核心處理
        ai_res = utils.process_ai(full_url, config['prompt_template'], model)
        
        # 整合標題、連結與 AI 回傳的 {"summary": "..."}
        record = {
            "title": item['title'],
            "link": full_url,
            "summary": ai_res.get("summary", "無摘要")
        }
        final_data.append(record)

    # 4. 儲存結果並更新歷史進度
    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    # 進度累加實際處理的數量，避免最後一整批不足 BATCH_SIZE 時 index 算錯
    progress["index"] += len(batch)
    with open(progress_file, "w") as f: 
        json.dump(progress, f)
        
    print(f"✅ 成功處理 {len(batch)} 筆新公告，目前總進度位置：{progress['index']}")

if __name__ == "__main__":
    main()
