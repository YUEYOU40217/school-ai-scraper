import json, os, utils
import google.generativeai as genai
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

BATCH_SIZE = 10 

def main():
    # 讀取設定檔
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # (測試階段暫時註解掉時間檢查，方便隨時執行)
    # taiwan_tz = timezone(timedelta(hours=8))
    # current_hour = datetime.now(taiwan_tz).hour
    # if current_hour not in config.get("active_hours", []):
    #     print(f"當前時間為 {current_hour} 點，非執行時段。")
    #     return

    # 1. 自動導航與清單抓取
    target_url = utils.find_announcement_page(config['urls'][0])
    
    selector_cfg = config.get('selector_config', {})
    row_selector = selector_cfg.get('row_selector', 'tr')
    link_selector = selector_cfg.get('link_selector', 'a')
    
    print(f"🔍 準備使用規則抓取連結... 區塊: '{row_selector}', 連結: '{link_selector}'")
    all_links = utils.fetch_links(target_url, row_selector, link_selector)
    
    # 🚨 【新增：無腦全輸出除錯檔】
    with open("debug_links.json", "w", encoding="utf-8") as f:
        json.dump(all_links, f, ensure_ascii=False, indent=2)
    print(f"👀 已經將剛剛爬到的 {len(all_links)} 筆原始連結，存進 debug_links.json！請打開確認。")
    
    if not all_links:
        print("⚠️ 警告：抓到的連結數量為 0！代表 config.json 裡面的 selector_config (抓取規則) 不符合現在的網頁結構。")
        return

    # 為了測試，強制將進度歸零
    progress = {"index": 0} 
    
    # 3. 分批截取處理
    idx = progress["index"]
    batch = all_links[idx : idx + BATCH_SIZE]

    # 初始化 Gemini
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    final_data = []
    if os.path.exists("announcements.json"):
        with open("announcements.json", "r", encoding="utf-8") as f:
            try: final_data = json.load(f)
            except: final_data = []

    for item in batch:
        full_url = urljoin(target_url, item['href'])
        print(f"🤖 正在請 AI 處理: {item['title']} -> {full_url}")
        
        ai_res = utils.process_ai(full_url, config['prompt_template'], model)
        
        record = {
            "title": item['title'],
            "link": full_url,
            "summary": ai_res.get("summary", "無摘要")
        }
        final_data.append(record)

    # 4. 儲存結果
    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 成功處理 {len(batch)} 筆新公告！")

if __name__ == "__main__":
    main()
