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
    # 使用極致輕量免費的 1.5-flash-lite
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
            
            # 從 config.json 讀取提示詞範本，並動態帶入內容與網址
            template = config.get("prompt_template", "")
            if not template:
                print("錯誤：config.json 中找不到 prompt_template")
                return
                
            prompt = template.format(content=content, url=url)
            
            response = model.generate_content(prompt)
            res_text = response.text.replace("```json", "").replace("
```", "").strip()
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
