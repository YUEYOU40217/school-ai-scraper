import json
import requests
import datetime
from bs4 import BeautifulSoup
from google import genai

def run():
    # 1. 讀取設定檔
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("錯誤：找不到 config.json，請確認檔案是否存在。")
        return

    # 2. 時間檢查邏輯 (若 config 沒有設定 active_hours 則預設全部時間都執行)
    current_hour = datetime.datetime.now().hour
    active_hours = config.get("active_hours", [])
    
    if active_hours and current_hour not in active_hours:
        print(f"現在是 {current_hour} 點，不在指定執行時段 {active_hours} 內。任務結束。")
        return

    # 3. 初始化 Gemini 客戶端
    client = genai.Client(api_key=config['api_key'])
    final_data = []

    # 4. 開始爬蟲
    for url in config.get('urls', []):
        print(f"正在爬取: {url}")
        try:
            # 加上 User-Agent 模擬瀏覽器，避免被網站擋掉
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            resp = requests.get(url, timeout=15, headers=headers)
            resp.raise_for_status() # 檢查連線是否成功
            
            soup = BeautifulSoup(resp.text, "html.parser")
            # 截取前 3000 個字元，避免 Prompt 過長
            content = soup.get_text(separator=' ', strip=True)[:3000]
            
            # 構建 Prompt
            prompt = f"""
            {config['prompt']}
            關鍵字: {config['keywords']}
            網頁內容: {content}
            
            請回傳一個符合 JSON 格式的陣列：[ {{"keywords": "...", "summary": "...", "link": "..."}} ]
            請不要包含任何 Markdown 代號(如 ```json)或額外解釋，只回傳純 JSON 字串。
            """
            
            # 呼叫 Gemini
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
            )
            
            # 清理 AI 回傳的雜訊
            res_text = response.text.strip().replace("```json", "").replace("```", "")
            data = json.loads(res_text)
            
            if isinstance(data, list):
                final_data.extend(data)
                
        except Exception as e:
            print(f"處理 {url} 時發生錯誤: {e}")

    # 5. 將結果寫入檔案
    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print("爬蟲任務順利完成，announcements.json 已更新。")

if __name__ == "__main__":
    run()
    
