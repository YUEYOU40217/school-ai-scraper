import os
import json
from google import genai
from utils import fetch_links_smart, fetch_detail_content, process_ai_batch

# 這是特別為台灣大專院校設計的 AI 提示詞範本（已套用嚴格格式限制）
AI_TEMPLATE = """你現在是台灣大專院校的公告解析與資料清理專家。
我會提供一批從學校網頁爬取下來的「可能包含雜訊」的原始資料。
每筆資料包含「學校名稱」、「標題」、「網址」、「列表頁週邊文字」與「內頁完整內文」。

請依照以下嚴格規則處理，並輸出 JSON 陣列格式：
1. 過濾雜訊：如果從標題或內文判斷這只是「常駐導覽連結」(如：回到首頁、聯絡我們、網頁版權聲明、隱私權政策、行事曆下載專區) 或「無效頁面」，請直接捨棄該筆資料。
2. 提取與轉換日期：找出公告發布日期。
   - 務必看懂台灣格式：如 115.06.15 或 115/06/15 需轉換為西元 2026-06-15。
   - 若出現 114-2 等學期制，請結合上下文推算合理西元日期。
   - 統一輸出標準格式：YYYY-MM-DD。找不到請填 "未知"。
3. 提取處室：判斷發布單位（例如：教務處、學務處）。若無則填 "未知"。
4. 摘要 (嚴格限制)：請僅使用「原始內文」進行精簡與排版（約 30-50 字）。絕對不要添加任何表情符號 (Emoji/貼圖)，也絕對不要額外撰寫、擴充或腦補原文沒有的內容。
5. 網址：保留該項目提供的原始網址 (link)。
6. 提取關鍵字：從內文中精準提取 1 到 5 個最重要的關鍵字 (keywords)，以陣列呈現。
7. 學校名稱：請保留傳入資料中的學校名稱 (school_name)。

回傳的 JSON 陣列格式範例：
[
  {
    "school_name": "正修科技大學",
    "title": "114學年度第2學期選課注意事項",
    "date": "2026-05-20",
    "department": "教務處",
    "summary": "本校114-2學期初選與加退選時程已公布，請同學依規定至選課系統操作，逾期不予受理。",
    "link": "https://...",
    "keywords": ["選課", "初選", "加退選"]
  }
]

以下是這批需處理的資料：
{batch_input}

請務必只回傳合法的 JSON 陣列字串，不需要 Markdown 標記或其他說明。"""


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[錯誤] 找不到 GEMINI_API_KEY 環境變數。")
        return

    client = genai.Client(api_key=api_key)

    # 1. 讀取並解析新的 config.json 結構
    if not os.path.exists('config.json'):
        print("[錯誤] 找不到 config.json 檔案。")
        return
        
    with open('config.json', 'r', encoding='utf-8') as f:
        try:
            config_data = json.load(f)
        except json.JSONDecodeError:
            print("[錯誤] config.json 格式錯誤。")
            return

    # 提取年份與站點列表
    allowed_years = config_data.get("allowed_years", [])
    sites = config_data.get("sites", [])

    if not sites:
        print("[錯誤] config.json 中沒有找到 'sites' 陣列設定。")
        return

    all_raw_data = []
    final_announcements = []

    # 2. 迴圈執行多學校爬取
    for site in sites:
        school_name = site.get("name", "未知學校")
        target_url = site.get("url")

        if not target_url:
            print(f"[跳過] {school_name} 缺少 'url' 欄位。")
            continue

        print(f"\n========================================")
        print(f"🏫 [開始執行] 目標: {school_name} | 網址: {target_url}")
        print(f"========================================")
        
        # 全量爬取列表
        source_name, raw_links = fetch_links_smart(target_url)
        if not raw_links:
            print(f"⚠️ [中斷] {school_name} 列表頁未撈到任何有效連結。")
            continue

        print(f"🔍 [深度抓取] 開始深入 {len(raw_links)} 個內頁抓取完整文字...")
        for idx, item in enumerate(raw_links):
            url = item['href']
            print(f" -> [{idx+1}/{len(raw_links)}] 抓取內文: {item['title']}")
            
            detail_content = fetch_detail_content(url)
            
            # 將 school_name 打包進去給 AI 看
            all_raw_data.append({
                "school_name": school_name,
                "title": item['title'],
                "url": url,
                "list_context": item['list_context'],
                "content": detail_content
            })

    # 3. 備份全量雜湊資料
    if all_raw_data:
        with open('raw_crawled_data.json', 'w', encoding='utf-8') as f:
            json.dump(all_raw_data, f, ensure_ascii=False, indent=4)
        print(f"\n✅ [備份完成] 原始網頁資料已寫入 raw_crawled_data.json")

        # 4. 送交 AI 處理
        print("\n🧠 [AI 處理] 開始將資料分批送交 Gemini 處理...")
        batch_size = 5  
        
        for i in range(0, len(all_raw_data), batch_size):
            batch = all_raw_data[i:i + batch_size]
            print(f" -> 正在處理第 {i+1} 到 {min(i+batch_size, len(all_raw_data))} 筆資料...")
            
            ai_result = process_ai_batch(batch, AI_TEMPLATE, client)
            if ai_result and isinstance(ai_result, list):
                final_announcements.extend(ai_result)

        # 5. 根據 allowed_years 進行嚴格過濾
        filtered_announcements = []
        if allowed_years:
            print(f"\n⏳ [年份過濾] 正在過濾非 {allowed_years} 年份的公告...")
            for ann in final_announcements:
                date_str = ann.get("date", "")
                try:
                    # 從 YYYY-MM-DD 取出前四碼年份
                    year = int(date_str.split("-")[0])
                    if year in allowed_years:
                        filtered_announcements.append(ann)
                except ValueError:
                    # 如果 AI 回傳 "未知" 或是格式出錯，這裡預設保留，以免錯殺
                    filtered_announcements.append(ann)
        else:
            filtered_announcements = final_announcements

        # 寫入最終乾淨資料
        with open('announcements.json', 'w', encoding='utf-8') as f:
            json.dump(filtered_announcements, f, ensure_ascii=False, indent=4)

        print(f"\n🎉 [大功告成] 處理完畢！共萃取出 {len(filtered_announcements)} 筆符合年份的有效公告，已存入 announcements.json")
    else:
        print("\n[結束] 未抓取到任何有效資料。")

if __name__ == "__main__":
    main()
