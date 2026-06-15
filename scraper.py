import os
import json
from google import genai
from utils import fetch_links_smart, fetch_detail_content, process_ai_batch

# 這是特別為台灣大專院校設計的 AI 提示詞範本
AI_TEMPLATE = """你現在是台灣大專院校的公告解析與資料清理專家。
我會提供一批從學校網頁爬取下來的「可能包含雜訊」的資料。
每筆資料包含「標題」、「網址」、「列表頁週邊文字」與「內頁完整內文」。

請依照以下嚴格規則處理，並輸出 JSON 陣列格式：
1. 過濾雜訊：如果從標題或內文判斷這只是「常駐導覽連結」(如：回到首頁、聯絡我們、網頁版權聲明、隱私權政策) 或「無效頁面」，請直接捨棄該筆資料，不要放進結果中。
2. 提取與轉換日期：從「列表頁週邊文字」或「內頁完整內文」中找出公告實際發布日期。
   - 務必看懂台灣特殊格式：如 115.06.15 或 115/06/15 需轉換為西元 2026-06-15 (民國年+1911)。
   - 若出現學期制如 114-2，請結合上下文推算，或取該學期的大約開始月份。
   - 統一輸出標準格式：YYYY-MM-DD。若真的找不到日期，請填 "未知"。
3. 提取處室：判斷發布單位（例如：教務處、學務處）。若無則填 "未知"。
4. 摘要：產生約 30-50 字的內容摘要。
5. 網址：請保留該項目提供的原始網址 (link)。

回傳的 JSON 陣列格式範例：
[
  {
    "title": "114學年度第2學期選課注意事項",
    "date": "2026-05-20",
    "department": "教務處",
    "summary": "說明114-2學期初選與加退選的時程規劃與選課系統操作注意事項...",
    "link": "https://..."
  }
]

以下是這批需處理的資料：
{batch_input}

請務必只回傳合法的 JSON 陣列字串，不需要 Markdown 標記或其他說明。"""


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    target_url = os.environ.get("TARGET_URL")
    
    if not api_key:
        print("[錯誤] 找不到 GEMINI_API_KEY 環境變數。")
        return
    if not target_url:
        print("[錯誤] 找不到 TARGET_URL 環境變數。")
        return

    client = genai.Client(api_key=api_key)
    print(f"[開始執行] 目標網址: {target_url}")
    
    # 【階段一：全量爬取原始資料】
    source_name, raw_links = fetch_links_smart(target_url)
    if not raw_links:
        print("[異常中斷] 列表頁未撈到任何連結。")
        return

    print(f"[深度抓取] 開始深入 {len(raw_links)} 個內頁抓取完整文字...")
    full_crawled_data = []
    
    for idx, item in enumerate(raw_links):
        url = item['href']
        print(f" -> [{idx+1}/{len(raw_links)}] 抓取內文: {item['title']}")
        
        detail_content = fetch_detail_content(url)
        
        full_crawled_data.append({
            "title": item['title'],
            "url": url,
            "list_context": item['list_context'],
            "content": detail_content
        })

    # 寫入最原始的資料庫（一分不差）
    with open('raw_crawled_data.json', 'w', encoding='utf-8') as f:
        json.dump(full_crawled_data, f, ensure_ascii=False, indent=4)
    print(f"\n[備份完成] 所有原始網頁資料已寫入 raw_crawled_data.json")

    # 【階段二：AI 智慧清理與萃取】
    print("\n[AI 處理] 開始將原始資料分批送交 Gemini 處理 (這可能需要幾分鐘)...")
    final_announcements = []
    batch_size = 5  # 每次送 5 筆給 AI，避免超出單次讀取上限
    
    for i in range(0, len(full_crawled_data), batch_size):
        batch = full_crawled_data[i:i + batch_size]
        print(f" -> 正在處理第 {i+1} 到 {min(i+batch_size, len(full_crawled_data))} 筆資料...")
        
        ai_result = process_ai_batch(batch, AI_TEMPLATE, client)
        
        if ai_result and isinstance(ai_result, list):
            # 這裡 AI 已經幫我們把垃圾連結都過濾掉了，只留下真正的公告
            final_announcements.extend(ai_result)

    # 寫入最終 AI 整理過的乾淨資料
    with open('announcements.json', 'w', encoding='utf-8') as f:
        json.dump(final_announcements, f, ensure_ascii=False, indent=4)

    print(f"\n[大功告成] AI 處理完畢！共萃取出 {len(final_announcements)} 筆有效公告，已存入 announcements.json")


if __name__ == "__main__":
    main()
