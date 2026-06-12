import os
import json
import requests
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def run():
    # 1. 讀取設定檔 (config.json)
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"無法讀取 config.json: {e}")
        return

    # 2. 時間守門員 (強制設定為台灣時間 UTC+8)
    taiwan_tz = timezone(timedelta(hours=8))
    current_hour = datetime.now(taiwan_tz).hour
    active_hours = config.get("active_hours", [])
    
    if active_hours and current_hour not in active_hours:
        print(f"現在是台灣時間 {current_hour} 點，不在執行時段內 {active_hours}，跳過爬蟲。")
        return

    print(f"現在是台灣時間 {current_hour} 點，開始執行爬蟲任務...")

    # 3. 設定 Gemini API
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("錯誤：找不到 GEMINI_API_KEY！")
        return
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-lite')

    final_data = []
    sel_config = config.get("selector_config", {})
    row_selector = sel_config.get("row_selector", "tr")
    link_selector = sel_config.get("link_selector", "a")
    template = config.get("prompt_template", "")

    # 4. 爬蟲核心
    for base_url in config.get('urls', []):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            resp = requests.get(base_url, timeout=15, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            rows = soup.find_all(row_selector)
            print(f"偵測到區塊數量: {len(rows)}")

            for row in rows:
                a_tag = row.find(link_selector) if row_selector != link_selector else row
                if not a_tag or not a_tag.get('href'): continue
                
                title = a_tag.get_text(strip=True)
                detail_url = urljoin(base_url, a_tag.get('href'))
                
                if "javascript:" in detail_url or detail_url == base_url: continue

                # 爬取內頁內容
                try:
                    inner_resp = requests.get(detail_url, timeout=10, headers=headers)
                    inner_soup = BeautifulSoup(inner_resp.text, "html.parser")
                    content = inner_soup.get_text(separator=' ', strip=True)[:2000]
                except:
                    content = title

                # AI 摘要
                prompt = template.format(content=content)
                try:
                    response = model.generate_content(prompt)
                    res_text = response.text.replace("```json", "").replace("
```", "").strip()
                    ai_data = json.loads(res_text)
                    final_data.append({
                        "title": title, "date": ai_data.get("date", "未提供"),
                        "department": ai_data.get("department", "未提供"),
                        "keywords": ai_data.get("keywords", []),
                        "summary": ai_data.get("summary", "內容請點擊連結查看。"),
                        "link": detail_url
                    })
                except:
                    final_data.append({"title": title, "summary": "摘要失敗", "link": detail_url})

        except Exception as e:
            print(f"發生錯誤: {e}")

    # 5. 存檔
    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"任務完成，共處理 {len(final_data)} 則公告。")

if __name__ == "__main__":
    run()
