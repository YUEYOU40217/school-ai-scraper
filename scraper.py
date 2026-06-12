import json, os, utils
import google.generativeai as genai
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

BATCH_SIZE = 10 

def main():
    # 讀取設定檔
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 1. 直接使用你設定的絕對網址，不再自動導航亂跑！
    target_url = config['urls'][0]
    print(f"🎯 鎖定目標網址: {target_url}")
    
    selector_cfg = config.get('selector_config', {})
    row_selector = selector_cfg.get('row_selector', '.mtitle')
    link_selector = selector_cfg.get('link_selector', 'a')
    
    print(f"🔍 準備使用規則抓取連結... 區塊: '{row_selector}', 連結: '{link_selector}'")
    all_links = utils.fetch_links(target_url, row_selector, link_selector)
    
    with open("debug_links.json", "w", encoding="utf-8") as f:
        json.dump(all_links, f, ensure_ascii=False, indent=2)
    print(f"👀 已經將剛剛爬到的 {len(all_links)} 筆原始連結，存進 debug_links.json！")
    
    if not all_links:
        print("⚠️ 警告：抓到的連結數量為 0！")
        return

    # 為了測試，強制將進度歸零
    progress = {"index": 0} 
    
    # 3. 分批截取處理
    idx = progress["index"]
    batch = all_links[idx : idx + BATCH_SIZE]

    # 初始化 Gemini (改用帶有 -latest 的完整名稱，解決 404 報錯)
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
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
