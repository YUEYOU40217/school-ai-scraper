import json
import requests
import datetime
import google.generativeai as genai  # 修正：改用正確的匯入方式
from bs4 import BeautifulSoup

def run():
    # 1. 讀取設定檔
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("錯誤：找不到 config.json")
        return

    # 2. 時間檢查
    current_hour = datetime.datetime.now().hour
    active_hours = config.get("active_hours", [])
    if active_hours and current_hour not in active_hours:
        print(f"現在是 {current_hour} 點，跳過執行。")
        return

    # 3. 初始化 Gemini (改用標準寫法)
    genai.configure(api_key=config['api_key'])
    model = genai.GenerativeModel('gemini-1.5-flash') # 使用穩定的 flash 模型

    final_data = []

    # 4. 爬蟲邏輯
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

    # 5. 存檔
    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run()
