import json
import os
import sys
import requests
from bs4 import BeautifulSoup
from google import genai

RESULTS_FILE = "announcements.json"

def run_scraper():
    # 1. 從 GitHub Secrets 讀取前端設定好的 JSON 資料
    config_str = os.environ.get("CONFIG_JSON")
    
    if not config_str:
        print("❌ 錯誤：找不到 CONFIG_JSON 設定，請檢查 GitHub Secrets 設定！")
        sys.exit(1)
        
    try:
        config = json.loads(config_str)
    except Exception as e:
        print(f"❌ 錯誤：CONFIG_JSON 格式不正確: {e}")
        sys.exit(1)

    # 2. 初始化 Gemini AI (自動使用安全箱內的 api_key)
    try:
        client = genai.Client(api_key=config.get('api_key'))
    except Exception as e:
        print(f"❌ 錯誤：Gemini Client 初始化失敗，請檢查 API Key: {e}")
        sys.exit(1)
    
    # 用來裝所有網址、所有公告的單一總清單
    final_announcements_list = []

    # 3. 巡邏前端設定的每一條 URL
    urls = config.get('urls', [])
    keywords = config.get('keywords', '')
    user_prompt = config.get('prompt', '')

    for url in urls:
        if not url.strip(): continue
        print(f"📡 正在抓取網址: {url}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8' # 避免中文亂碼
            
            soup = BeautifulSoup(response.text, "html.parser")
            web_content = soup.get_text(separator=' ', strip=True)[:2500] # 抓取前2500字內文

            # 4. 強制 AI 只能輸出 keywords, summary, link 三個欄位
            strict_prompt = f"""
            使用者核心指示：{user_prompt}
            請特別過濾並留意這些監控關鍵字：{keywords}
            
            任務要求：
            請從下方的網頁內容中，找出符合要求的公告資訊。
            每一條公告，你「只能」且「必須」整理出以下三個欄位：
            1. keywords: 這篇公告的關鍵字
            2. summary: 這篇公告的內容簡述
            3. link: 這篇公告在內文中對應的完整連結或相對路徑（如果內文完全沒有該公告的連結，請填寫空字串 ""）
            
            網頁內容：
            {web_content}
            
            請嚴格以標準 JSON 陣列格式回傳，不要包含任何 Markdown 標記（如 ```json）或任何額外說明的廢話。格式範例如下：
            [
              {{"keywords": "關鍵字1, 關鍵字2", "summary": "這是內容簡述", "link": "[https://example.com/news/1](https://example.com/news/1)"}},
              {{"keywords": "關鍵字3", "summary": "這是沒有連結的公告", "link": ""}}
            ]
            """

            # 呼叫 Gemini
            ai_response = client.models.generate_content(
                model="gemini-3.1-Flash-Lite",
                contents=strict_prompt,
            )

            # 清理 AI 回傳內容並轉成 Python 列表
            clean_text = ai_response.text.replace("```json", "").replace("```", "").strip()
            ai_data = json.loads(clean_text)

            if isinstance(ai_data, list):
                for item in ai_data:
                    formatted_item = {
                        "keywords": item.get("keywords", ""),
                        "summary": item.get("summary", ""),
                        "link": item.get("link", "")
                    }
                    final_announcements_list.append(formatted_item)
                    
            print(f"✅ 網址 {url} 處理成功。")

        except Exception as e:
            print(f"❌ 處理網址 {url} 時發生錯誤: {e}")

    # 5. 最終大合流：不論幾條網址，全部存進這唯一一個 JSON 檔案
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(final_announcements_list, f, ensure_ascii=False, indent=2)
    
    print(f"🎉 全部任務完成！所有結果已寫入 {RESULTS_FILE}")

if __name__ == "__main__":
    run_scraper()
