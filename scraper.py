import json, os, utils
from google import genai
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

    for item in batch:
        full_url = urljoin(target_url, item['href'])
        print(f"🤖 正在請 AI 處理: {item['title']} -> {full_url}")
        
        # 傳入 client 而不是 model
        ai_res = utils.process_ai(full_url, config['prompt_template'], client)
        
        record = {
            "title": item['title'],
            "link": full_url,
            "summary": ai_res.get("summary", "無摘要")
        }
        final_data.append(record)

    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 成功處理 {len(batch)} 筆新公告！")

if __name__ == "__main__":
    main()
