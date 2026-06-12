import os
import json
import requests
import datetime
import google.generativeai as genai
from bs4 import BeautifulSoup

def run():
    # 1. 讀取設定檔
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"無法讀取 config.json: {e}")
        return

    # 2. 時間檢查 (守門員邏輯)
    current_hour = datetime.datetime.now().hour
    active_hours = config.get("active_hours", [])
    if active_hours and current_hour not in active_hours:
        print(f"現在是 {current_hour} 點，不在執行時段內，跳過。")
        return

    # 3. 設定 API (從 GitHub Secrets 安全讀取)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("錯誤：找不到 GEMINI_API_KEY 環境變數！")
        return
        
    genai.configure(api_key=api_key)
    # 關鍵修改：指定使用極致輕量免費的 1.5-flash-lite
    model = genai.GenerativeModel('gemini-1.5-flash-lite')

    final_data = []

    # 4. 爬蟲核心邏輯
    for url in config.get('urls', []):
        try:
            print(f"正在爬取: {url}")
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            content = soup.get_text(separator=' ', strip=True)[:3000]
            
            prompt = f"""
            你是一位專業的資訊摘要秘書。請根據網頁內容整理公告。
            
            任務要求：
            1. 提取所有關鍵資訊：時間、對象、地點、申請方式、重要說明。
            2. 目標是讓使用者讀完摘要後「完全不需要點擊連結」。若網頁內容過少，請務必標註「內容僅有標題，建議點擊詳情」。
            3. 自動產生 3-5 個關鍵標籤。
            
            網頁內容如下:
            {content}
            
            請嚴格以 JSON 格式回傳陣列，如下：
            [
                {{
                    "keywords": ["標籤1", "標籤2"],
                    "summary": "這裡填寫詳細摘要，將所有重要資訊條列式說明",
                    "link": "{url}"
                }}
            ]
            """
            
            response = model.generate_content(prompt)
            res_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(res_text)
            
            if isinstance(data, list):
                final_data.extend(data)
                
        except Exception as e:
            print(f"爬取 {url} 失敗: {e}")

    # 5. 存檔
    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print("爬蟲任務順利完成！檔案已更新至 announcements.json")

if __name__ == "__main__":
    run()
            
