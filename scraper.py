import json
import requests
import datetime
import google.generativeai as genai
from bs4 import BeautifulSoup

def run():
    # 讀取設定檔
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"無法讀取 config.json: {e}")
        return

    # 時間檢查
    current_hour = datetime.datetime.now().hour
    active_hours = config.get("active_hours", [])
    if active_hours and current_hour not in active_hours:
        print(f"現在是 {current_hour} 點，跳過執行。")
        return

    # 設定 API
    genai.configure(api_key=config['api_key'])
    model = genai.GenerativeModel('gemini-1.5-flash')

    final_data = []

    # 爬蟲邏輯
    for url in config.get('urls', []):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")
            content = soup.get_text(separator=' ', strip=True)[:3000]
            
            prompt = f"""
            {config['prompt']}
            關鍵字: {config['keywords']}
            網頁內容: {content}
            請回傳純 JSON 格式陣列: [ {{"keywords": "...", "summary": "...", "link": "..."}} ]
            """
            
            response = model.generate_content(prompt)
            
            # 清理輸出
            res_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(res_text)
            
            if isinstance(data, list):
                final_data.extend(data)
                
        except Exception as e:
            print(f"爬取 {url} 失敗: {e}")

    # 存檔
    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print("爬蟲任務順利完成！")

if __name__ == "__main__":
    run()

