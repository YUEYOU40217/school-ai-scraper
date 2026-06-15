import os
import json
import uuid
import time
from urllib.parse import urlparse
from collections import defaultdict
from google import genai
from utils import fetch_links_smart, fetch_detail_content, process_ai_batch

# ========================================================
# 1. AI 提示詞定義
# ========================================================
AI_TEMPLATE = """你現在是台灣大專院校的公告解析與資料清理專家。
我會提供一批從學校網頁爬取下來的「可能包含雜訊」的原始資料。
每筆資料包含「uuid」、「學校名稱」、「標題」、「網址」、「列表頁週邊文字」與「內頁完整內文」。

【目標年份與自動時間鎖】
本次爬取的目標西元年為：【{target_years}】。
你必須根據這些年份，自動在背景推算並只保留屬於這些年份與對應台灣學學期的公告。合格的範圍必須包含：
1. 公告日期明確屬於上述指定的西元年份.
2. 公告內文提及該些年份對應的台灣學年度與學期。
★ 鐵律：若公告「不屬於」上述自動推算的任何目標年份或對應學期，請直接過濾丟棄。

請依照以下嚴格規則處理，並輸出 JSON 陣列格式：
1. 過濾雜訊：如果是常駐導覽連結或無效頁面，請直接捨棄。
2. 嚴格對齊 UUID：必須完整且原封不動地保留傳入資料原有的 `uuid`。
3. 歸類 (category)：精準歸類為：「招生訊息」、「學務公告」、「教務公告」、「演講與活動」、「徵才資訊」、「招標與採購」、「其他」。
4. 提取與轉換日期：統一輸出標準格式：YYYY-MM-DD。找不到請填 "未知"。
5. 提取處室：判斷發布單位。若無則填 "未知"。
6. 摘要 (嚴格限制)：僅使用原始內文進行精簡（約 30-50 字），不添加表情符號，不腦補。
7. 網址：保留該項目提供的原始網址 (link)。
8. 提取關鍵字：從內文中精準提取 1 到 5 個最重要的關鍵字 (keywords)，以陣列呈現。
9. 學校名稱：請保留傳入資料中的學校名稱 (school_name)。

以下是這批需處理的資料：
{batch_input}"""

# ========================================================
# 2. 輔助函數：自動萃取學校網址簡稱
# ========================================================
def get_url_short_name(url):
    """從網址中自動萃取學校簡稱（例如：https://www.csu.edu.tw/ -> csu）"""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        parts = domain.split('.')
        # 排除常見的前綴
        if len(parts) >= 3:
            for part in parts:
                if part not in ['www', 'mail', 'office', 'my', 'cc', 'ws1']:
                    return part
        return parts[0]
    except:
        return "school"

# ========================================================
# 3. 主程式執行邏輯
# ========================================================
def main():
    # 檢查 API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[錯誤] 找不到 GEMINI_API_KEY 環境變數。")
        return

    client = genai.Client(api_key=api_key)

    # 讀取設定檔
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
    current_template = AI_TEMPLATE.format(target_years=target_years_str, batch_input="{batch_input}")

    all_raw_data = []
    site_meta_map = {}

    # --------------------------------------------------------
    # 階段 A: 爬取所有網頁內容，並「每爬完一站就單獨存一個 raw 檔」
    # --------------------------------------------------------
    for site in sites:
        school_name = site.get("name", "未知學校")
        target_url = site.get("url")

        if not target_url:
            continue

        print(f"\n========================================")
        print(f"[開始執行] 目標: {school_name} | {target_url}")
        print(f"========================================")
        
        source_name, raw_links = fetch_links_smart(target_url)
        if not raw_links:
            continue
            
        # 取得乾淨的短檔名 (不再加任何數字後綴)
        short_name = get_url_short_name(target_url)
        site_meta_map[target_url] = {
            "name": f"{school_name} - {source_name}",
            "url": target_url,
            "short_name": short_name
        }

        # 用來裝「這一個單一目標」的原始資料
        current_site_raw_data = []

        for idx, item in enumerate(raw_links):
            url = item['href']
            print(f" -> [{idx+1}/{len(raw_links)}] 抓取內文: {item['title']}")
            detail_content = fetch_detail_content(url)
            
            data_item = {
                "uuid": str(uuid.uuid4()),
                "school_name": school_name,
                "title": item['title'],
                "link": url,
                "list_context": item['list_context'],
                "content": detail_content,
                "source_url": target_url
            }
            
            current_site_raw_data.append(data_item)
            all_raw_data.append(data_item)

        # ✨ 新功能：這站爬完後，立刻輸出一個這站專屬的 raw 檔案讓你檢查
        if current_site_raw_data:
            raw_filename = f"raw_crawled_{short_name}.json"
            with open(raw_filename, 'w', encoding='utf-8') as f:
                json.dump(current_site_raw_data, f, ensure_ascii=False, indent=4)
            print(f"📦 [單站備份] {school_name} 的原始抓取資料已存入 {raw_filename}，你可以馬上打開來檢查爬了什麼！")

    if not all_raw_data:
        print("\n[結束] 未抓取到任何有效資料。")
        return

    # --------------------------------------------------------
    # 階段 B: 送交 AI 批次處理
    # --------------------------------------------------------
    print("\n🤖 開始將所有資料分批送交 Gemini AI 進行過濾與清理...")
    final_announcements = []
    batch_size = 15  
    
    for i in range(0, len(all_raw_data), batch_size):
        batch = all_raw_data[i:i + batch_size]
        print(f" -> 正在處理第 {i+1} 到 {min(i+batch_size, len(all_raw_data))} 筆資料...")
        ai_result = process_ai_batch(batch, current_template, client)
        
        if ai_result and isinstance(ai_result, list):
            # 還原來源網址對應，以便後續分檔
            uuid_to_source = {item["uuid"]: item["source_url"] for item in batch}
            for ann in ai_result:
                ann_uuid = ann.get("uuid")
                if ann_uuid in uuid_to_source:
                    ann["source_url"] = uuid_to_source[ann_uuid]
            final_announcements.extend(ai_result)
        
        if i + batch_size < len(all_raw_data):
            time.sleep(8) # 減緩頻率避免塞車

    # --------------------------------------------------------
    # 階段 C: 年份過濾
    # --------------------------------------------------------
    filtered_announcements = []
    if allowed_years:
        for ann in final_announcements:
            date_str = ann.get("date", "")
            try:
                year = int(date_str.split("-")[0])
                if year in allowed_years:
                    filtered_announcements.append(ann)
            except:
                filtered_announcements.append(ann)
    else:
        filtered_announcements = final_announcements

    # ========================================================
    # 階段 D: 分流輸出至獨立的 JSONL 檔案
    # ========================================================
    print("\n📂 開始打包最終乾淨資料...")
    
    grouped_announcements = defaultdict(list)
    for ann in filtered_announcements:
        source_url = ann.get("source_url")
        if source_url:
            grouped_announcements[source_url].append(ann)

    for url, meta in site_meta_map.items():
        short_name = meta["short_name"] 
        site_announcements = grouped_announcements.get(url, [])
        total_count = len(site_announcements)
        
        # 乾淨的檔名：announcements_csu.jsonl
        filename = f"announcements_{short_name}.jsonl"
        
        with open(filename, 'w', encoding='utf-8') as f:
            # 第一行：網站元資料 (Header)
            header_object = {
                "source_name": meta["name"],
                "source_link": meta["url"],
                "total_count": total_count
            }
            f.write(json.dumps(header_object, ensure_ascii=False) + '\n')
            
            # 第二行開始：打平的公告 (Body)
            for ann in site_announcements:
                keywords_list = ann.get("keywords", [])
                if not isinstance(keywords_list, list):
                    keywords_list = [str(keywords_list)]
                    
                ann_object = {
                    "uuid": ann.get("uuid"),
                    "short_name": short_name,
                    "title": ann.get("title"),
                    "link": ann.get("link"),
                    "keywords": keywords_list
                }
                f.write(json.dumps(ann_object, ensure_ascii=False) + '\n')
        
        print(f"✅ [打包完畢] 網站【{meta['name']}】已獨立輸出至 {filename}，共 {total_count} 條有效公告。")

if __name__ == "__main__":
    main()
