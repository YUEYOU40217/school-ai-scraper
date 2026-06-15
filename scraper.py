import os
import json
import uuid
import time
from google import genai
from utils import fetch_links_smart, fetch_detail_content, process_ai_batch

AI_TEMPLATE = """你現在是台灣大專院校的公告解析與資料清理專家。
我會提供一批從學校網頁爬取下來的「可能包含雜訊」的原始資料。
每筆資料包含「uuid」、「學校名稱」、「標題」、「網址」、「列表頁週邊文字」與「內頁完整內文」。

【目標年份與自動時間鎖】
本次爬取的目標西元年為：【{target_years}】。
你必須根據這些年份，自動在背景推算並只保留屬於這些年份與對應台灣學學期的公告。合格的範圍必須包含：
1. 公告日期明確屬於上述指定的西元年份。
2. 公告內文提及該些年份對應的台灣學年度與學期。
   - 例如：若包含 2026，則自動包含「114-2 (114下)」與「115-1 (115上)」。
   - 例如：若包含 2025，則自動包含「113-2 (113下)」與「114-1 (114上)」。
★ 鐵律：若公告「不屬於」上述自動推算的任何目標年份或對應學期（例如更舊的歷史資料），請直接「整條過濾丟棄」，絕對不要放進輸出中。

請依照以下嚴格規則處理，並輸出 JSON 陣列格式：
1. 過濾雜訊：如果從標題或內文判斷這只是「常駐導覽連結」(如：回到首頁、聯絡我們、網頁版權聲明、隱私權政策、行事曆下載專區) 或「無效頁面」，請直接捨棄該筆資料。
2. 嚴格對齊 UUID：必須完整且原封不動地保留傳入資料原有的 `uuid`，絕對不可遺漏、修改或錯配。
3. 歸類 (category)：請根據公告內容，精準歸類為以下其中一種：「招生訊息」、「學務公告」、「教務公告」、「演講與活動」、「徵才資訊」、「招標與採購」、「其他」。
4. 提取與轉換日期：找出公告發布日期。
   - 務必看懂台灣格式：如 115.06.15 或 115/06/15 需轉換為西元 2026-06-15。
   - 統一輸出標準格式：YYYY-MM-DD。找不到請填 "未知"。
5. 提取處室：判斷發布單位（例如：教務處、學務處）。若無則填 "未知"。
6. 摘要 (嚴格限制)：請僅使用「原始內文」進行精簡與排版（約 30-50 字）。絕對不要添加任何表情符號，也絕對不要額外撰寫、擴充或腦補原文沒有的內容。
7. 網址：保留該項目提供的原始網址 (link)。
8. 提取關鍵字：從內文中精準提取 1 到 5 個最重要的關鍵字 (keywords)，以 JSON 陣列呈現。
9. 學校名稱：請保留傳入資料中的學校名稱 (school_name)。

【輸出範例結構】
[
  {{
    "uuid": "傳入的原始uuid",
    "school_name": "學校名稱",
    "title": "公告標題",
    "category": "歸類結果",
    "date": "YYYY-MM-DD",
    "department": "發布處室",
    "summary": "摘要內容...",
    "link": "原始網址",
    "keywords": ["關鍵字1", "關鍵字2"]
  }}
]

以下是這批需處理的資料：
{batch_input}"""

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[錯誤] 找不到 GEMINI_API_KEY 環境變數。")
        return

    client = genai.Client(api_key=api_key)

    if not os.path.exists('config.json'):
        print("[錯誤] 找不到 config.json 檔案。")
        return
        
    with open('config.json', 'r', encoding='utf-8') as f:
        try:
            config_data = json.load(f)
        except json.JSONDecodeError:
            print("[錯誤] config.json 格式錯誤。")
            return

    allowed_years = config_data.get("allowed_years", [])
    sites = config_data.get("sites", [])

    if not sites:
        print("[錯誤] config.json 中沒有找到 'sites' 陣列設定。")
        return

    target_years_str = ", ".join(map(str, allowed_years)) if allowed_years else "2026"

    current_template = AI_TEMPLATE.format(
        target_years=target_years_str,
        batch_input="{batch_input}"
    )

    all_raw_data = []
    final_announcements = []

    for site in sites:
        school_name = site.get("name", "未知學校")
        target_url = site.get("url")

        if not target_url:
            print(f"[跳過] {school_name} 缺少 'url' 欄位。")
            continue

        print(f"\n========================================")
        print(f"[開始執行] 目標: {school_name} | 網址: {target_url}")
        print(f"========================================")
        
        source_name, raw_links = fetch_links_smart(target_url)
        if not raw_links:
            print(f"[中斷] {school_name} 列表頁未撈到任何有效連結。")
            continue

        print(f"[深度抓取] 開始深入 {len(raw_links)} 個內頁抓取完整文字...")
        for idx, item in enumerate(raw_links):
            url = item['href']
            print(f" -> [{idx+1}/{len(raw_links)}] 抓取內文: {item['title']}")
            
            detail_content = fetch_detail_content(url)
            item_uuid = str(uuid.uuid4())
            
            all_raw_data.append({
                "uuid": item_uuid,
                "school_name": school_name,
                "title": item['title'],
                "link": url,
                "list_context": item['list_context'],
                "content": detail_content,
                "source_url": target_url
            })

    if all_raw_data:
        with open('raw_crawled_data.json', 'w', encoding='utf-8') as f:
            json.dump(all_raw_data, f, ensure_ascii=False, indent=4)
        print(f"\n[備份完成] 原始網頁資料已寫入 raw_crawled_data.json")

        print("\n[AI 處理] 開始將資料分批送交 Gemini 3.1 Flash-Lite 處理...")
        # 放大批次至 15 筆，減少呼叫次數
        batch_size = 15  
        
        for i in range(0, len(all_raw_data), batch_size):
            batch = all_raw_data[i:i + batch_size]
            print(f" -> 正在處理第 {i+1} 到 {min(i+batch_size, len(all_raw_data))} 筆資料...")
            
            ai_result = process_ai_batch(batch, current_template, client)
            if ai_result and isinstance(ai_result, list):
                uuid_to_source = {item["uuid"]: item["source_url"] for item in batch}
                
                for ann in ai_result:
                    ann_uuid = ann.get("uuid")
                    if ann_uuid in uuid_to_source:
                        ann["source_url"] = uuid_to_source[ann_uuid]
                
                final_announcements.extend(ai_result)
            
            # 預防性輕踩煞車：若還有下一批，主動原地休息 10 秒（配合底層重試機制，效率最高）
            if i + batch_size < len(all_raw_data):
                print("   [系統] 順應 API 正常速率，預防性暫停 10 秒...")
                time.sleep(10)

        filtered_announcements = []
        if allowed_years:
            print(f"\n[年份過濾] 正在過濾非 {allowed_years} 年份的公告...")
            for ann in final_announcements:
                date_str = ann.get("date", "")
                try:
                    year = int(date_str.split("-")[0])
                    if year in allowed_years:
                        filtered_announcements.append(ann)
                except ValueError:
                    filtered_announcements.append(ann)
        else:
            filtered_announcements = final_announcements

        # 確保儲存為最嚴格壓縮、不帶換行的單行 JSON
        with open('announcements.json', 'w', encoding='utf-8') as f:
            json.dump(filtered_announcements, f, ensure_ascii=False, separators=(',', ':'))

        print(f"\n[處理完畢] 共萃取出 {len(filtered_announcements)} 筆符合年份的有效公告，已存入 announcements.json")
    else:
        print("\n[結束] 未抓取到任何有效資料。")

if __name__ == "__main__":
    main()
