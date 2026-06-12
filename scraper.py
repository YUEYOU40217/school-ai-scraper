import os
import json
import requests
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def run():
    # 1. 讀取設定檔
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"無法讀取 config.json: {e}")
        return

    # 2. 終極時間守門員 (強制台灣時間)
    taiwan_tz = timezone(timedelta(hours=8))
    now = datetime.now(taiwan_tz)
    current_hour = now.hour
    active_hours = config.get("active_hours", [])
    
    if current_hour not in active_hours:
        print(f"現在是台灣時間 {current_hour} 點，不在設定的執行時段 {active_hours} 內，跳過。")
        return

    print(f"現在是台灣時間 {current_hour} 點，符合執行時段，開始執行爬蟲任務...")

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
    template = config.get("prompt_template", "")

    # 4. 強制掃描爬蟲核心
    for base_url in config.get('urls', []):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            resp = requests.get(base_url, timeout=15, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 嘗試原本的 row_selector
            rows = soup.find_all(row_selector)
            
            # 如果找不到 row，強迫抓取頁面上所有 <a> 標籤，保證有東西爬
            if not rows:
                print("未找到指定 row_selector，強制切換為全網頁連結掃描模式...")
                rows = soup.find_all('a')
            
            print(f"DEBUG: 本次共掃描到 {len(rows)} 個潛在連結點")
            
            for row in rows:
                # 判斷是否為連結，如果是 row 裡面包 a，則提取 a；如果是 a 本身則直接處理
                a_tag = row if row.name == 'a' else row.find('a')
                if not a_tag or not a_tag.get('href'): continue
                
                title = a_tag.get_text(strip=True)
                detail_url = urljoin(base_url, a_tag.get('href'))
                
                # 過濾無效連結
                if "javascript:" in detail_url or len(title) < 5: continue

                # 爬取內頁
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
                    res_text = response.text.replace("```json", "").replace("```", "").strip()
                    ai_data = json.loads(res_text)
                    final_data.append({
                        "title": title, "date": ai_data.get("date", "未提供"),
                        "department": ai_data.get("department", "未提供"),
                        "keywords": ai_data.get("keywords", []),
                        "summary": ai_data.get("summary", "內容請點擊連結查看。"),
                        "link": detail_url
                    })
                except:
                    final_data.append({"title": title, "summary": "內容請點擊連結查看。", "link": detail_url})
        except Exception as e:
            print(f"爬取失敗: {e}")

    # 5. 存檔
    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"任務完成，共處理 {len(final_data)} 則公告。")

if __name__ == "__main__":
    run()
