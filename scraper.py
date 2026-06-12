import os
import json
import requests
import datetime
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

    # 2. 時間守門員邏輯
    current_hour = datetime.datetime.now().hour
    active_hours = config.get("active_hours", [])
    if active_hours and current_hour not in active_hours:
        print(f"現在是 {current_hour} 點，不在執行時段內 ({active_hours})，跳過爬蟲。")
        return

    # 3. 設定 Gemini API
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("錯誤：找不到 GEMINI_API_KEY 環境變數！請確認 GitHub Secrets 設定。")
        return
        
    genai.configure(api_key=api_key)
    # 使用極致輕量免費的 1.5-flash-lite 模型
    model = genai.GenerativeModel('gemini-1.5-flash-lite')

    final_data = []
    
    # 讀取網頁結構配置 (selector_config)
    sel_config = config.get("selector_config", {})
    row_selector = sel_config.get("row_selector", "tr")
    link_selector = sel_config.get("link_selector", "a")
    template = config.get("prompt_template", "")

    # 4. 配置驅動型「兩層式爬蟲」核心邏輯
    for base_url in config.get('urls', []):
        try:
            print(f"正在爬取總列表: {base_url}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            resp = requests.get(base_url, timeout=15, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 第一層：依照 config 設定的區塊標籤 (預設為 tr) 切出每一列公告
            rows = soup.find_all(row_selector)
            print(f"依配置 [{row_selector}] 偵測到公告區塊數量: {len(rows)}")

            for row in rows:
                # 依照 config 設定的標籤 (預設為 a) 抓取超連結
                a_tag = row.find(link_selector) if row_selector != link_selector else row
                
                # 確保該區塊內真的有有效的超連結
                if not a_tag or not a_tag.get('href') or not a_tag.get_text(strip=True):
                    continue
                
                title = a_tag.get_text(strip=True)
                relative_url = a_tag.get('href')
                # 組合出完整的個別公告網址
                detail_url = urljoin(base_url, relative_url)
                
                # 過濾無效的或裝飾性的連結
                if "javascript:" in detail_url or detail_url == base_url:
                    continue

                print(f"發現公告: {title} | 專屬連結: {detail_url}")
                
                # 第二層：爬取各別公告「內頁」的文字內容
                announcement_content = ""
                try:
                    inner_resp = requests.get(detail_url, timeout=10, headers=headers)
                    inner_soup = BeautifulSoup(inner_resp.text, "html.parser")
                    # 擷取內頁文字並限制字數，避免超過 AI 處理上限
                    announcement_content = inner_soup.get_text(separator=' ', strip=True)[:2000]
                except Exception as inner_e:
                    print(f"讀取內頁失敗，改用列表文字: {inner_e}")
                    announcement_content = row.get_text(separator=' ', strip=True)

                # 準備提示詞
                if not template:
                    print("錯誤：config.json 找不到 prompt_template 配置")
                    continue
                    
                prompt = template.format(content=announcement_content)
                
                # 呼叫 Gemini 進行摘要
                try:
                    response = model.generate_content(prompt)
                    # 清理可能夾帶的 Markdown 標籤，確保是乾淨的 JSON 字串
                    res_text = response.text.replace("```json", "").replace("```", "").strip()
                    ai_data = json.loads(res_text)
                    
                    # 將 AI 的結果與爬蟲抓到的詳細連結組合起來
                    final_data.append({
                        "title": title,
                        "date": ai_data.get("date", "未提供"),
                        "department": ai_data.get("department", "未提供"),
                        "keywords": ai_data.get("keywords", []),
                        "summary": ai_data.get("summary", "無法生成摘要"),
                        "link": detail_url  # 注入真實的專屬個別連結
                    })
                    
                except Exception as ai_e:
                    print(f"AI 摘要失敗，使用備用格式: {ai_e}")
                    # 若 AI 處理失敗，仍保留標題與連結
                    final_data.append({
                        "title": title,
                        "date": "未提供",
                        "department": "未提供",
                        "keywords": [],
                        "summary": "內容請點擊連結查看細節。",
                        "link": detail_url
                    })

        except Exception as e:
            print(f"爬取總列表失敗: {e}")

    # 5. 將結果存檔回 JSON
    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"任務順利完成！共處理並摘要了 {len(final_data)} 則個別公告。")

if __name__ == "__main__":
    run()
