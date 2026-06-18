import os
import glob
import json
import re
import uuid
import time
from datetime import datetime
from google import genai

MODEL_NAME = "gemini-3.1-flash-lite"
ai_client = None

def init_ai(api_key):
    global ai_client
    if api_key:
        try:
            ai_client = genai.Client(api_key=api_key)
            return True
        except Exception as e:
            print(f"[錯誤] AI 初始化失敗: {e}")
            return False
    return False

def clean_ai_response(text):
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text.strip()

def clean_url(url):
    """清理網址，提取關鍵路徑部分，防止網域變動或絕對/相對路徑導致比對失敗"""
    if not url:
        return ""
    url = url.strip()
    # 提取 /p/... 或 /var/file/... 等後半段路徑
    match = re.search(r'(/(p|var)/.+)$', url)
    return match.group(1) if match else url

def process_single_html_with_retry(site_name, file_path):
    """精確解析單頁 HTML，並內建 429 限流自動重試機制"""
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 自動獲取當前執行系統的西元年 (例如 2026)
    current_year = datetime.now().year

    prompt = f"""
你是一個嚴格的網頁資料結構化專家。請將以下 HTML 中的「公告/新聞」提取出來，並「嚴格」遵守 JSONL 格式輸出。

【嚴格輸出格式要求】：
1. 絕對不要包含任何 Markdown 標籤 (例如不要寫 ```jsonl)。
2. 第一行是來源統計：
{{"source_name": "{site_name}", "source_link": "該網站網址", "total_count": 0}}
3. 第二行開始，每一行代表一個公告。UUID 請留空。
{{"uuid": "", "date": "YYYY-MM-DD", "short_name": "csu", "title": "公告標題", "link": "完整超連結", "keywords": ["字1", "字2", "字3", "字4", "字5"]}}

【重要原則 - 日期 (date) 欄位解析】：
- 必須輸出 YYYY-MM-DD 的西元年格式。
- 若公告僅有月、日而缺少年份，請一律推測為當前西元年份：【 {current_year} 】年。
- 【台灣學年度推算公式】：
  若出現「N學年度-1 (上學期)」，西元年為 N + 1911。
  若出現「N學年度-2 (下學期)」，西元年為 N + 1911 + 1。
  (例如：114-1 為 2025 年；114-2 為 2026 年；115-1 為 2026 年)。
- 若標示純民國年(如113年)，請加1911轉換為西元年。

【重要原則 - 關鍵字 (keywords) 欄位解析】：
- 陣列【必須且絕對只能剛好是 5 個元素】。

待處理 HTML：
--- {os.path.basename(file_path)} ---
{html_content}
"""
    if not ai_client:
        return None

    # 限流重試邏輯
    retries = 5
    delay = 4.5  # 基本每次呼叫都故意等 4.5 秒，確保一分鐘不超過 15 次 (15 * 4 = 60秒)
    
    for attempt in range(retries):
        try:
            # 呼叫前先進行冷卻防護
            time.sleep(delay)
            
            response = ai_client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            return clean_ai_response(response.text)
        except Exception as e:
            # 如果偵測到 429 或是 ResourceExhausted 限制
            if "429" in str(e) or "ResourceExhausted" in str(e):
                wait_time = 12 * (attempt + 1)
                print(f"      [觸發限流] API 達到每分鐘上限，暫停 {wait_time} 秒後重試...")
                time.sleep(wait_time)
            else:
                print(f"      [錯誤] 呼叫 Gemini 失敗: {e}")
                return None
    return None

def merge_and_save_jsonl(site_name, ai_jsonl_chunks, output_file_path):
    existing_items = []
    metadata = {"source_name": site_name, "source_link": "", "total_count": 0}

    # 1. 讀取舊資料
    if os.path.exists(output_file_path):
        with open(output_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    if "link" in data and "uuid" in data:
                        existing_items.append(data)
                    elif "source_name" in data:
                        metadata["source_link"] = data.get("source_link", "")
                except json.JSONDecodeError:
                    pass

    # 2. 處理 AI 新抓出來的資料
    for chunk in ai_jsonl_chunks:
        if not chunk: continue
        for line in chunk.split("\n"):
            if not line.strip(): continue
            try:
                data = json.loads(line)
                if "source_name" in data and not metadata["source_link"]:
                    metadata["source_link"] = data.get("source_link", "")
                elif "link" in data:
                    new_title = data.get("title", "").strip()
                    new_link = data.get("link", "").strip()
                    new_clean_link = clean_url(new_link)

                    # 【核心機制】雙重穩定鎖定：檢查歷史資料
                    matched_old_item = None
                    for old_item in existing_items:
                        old_title = old_item.get("title", "").strip()
                        old_link = old_item.get("link", "").strip()
                        old_clean_link = clean_url(old_link)

                        # 如果 標題完全一樣 或者 清理後的網址後半段完全一樣
                        if (new_title == old_title) or (new_clean_link and new_clean_link == old_clean_link):
                            matched_old_item = old_item
                            break

                    # 格式規範：確保關鍵字有 5 個
                    keywords = data.get("keywords", [])
                    if not isinstance(keywords, list): keywords = []
                    keywords = (keywords + ["公告", "資訊", "校園", "最新消息", "無"])[:5]
                    data["keywords"] = keywords

                    if matched_old_item:
                        # 找到了！【天條】：絕對不改變原本的 UUID
                        data["uuid"] = matched_old_item["uuid"]
                        
                        # 【天條】：如果舊資料本來就有合理的歷史日期，不要被新 AI 推測的年份蓋掉！
                        if matched_old_item.get("date") and matched_old_item["date"] != "1970-01-01":
                            data["date"] = matched_old_item["date"]
                        
                        # 順便更新可能變動的網址或欄位格式
                        data["link"] = new_link
                        data["title"] = new_title

                        # 更新舊列表中的資料
                        for idx, oi in enumerate(existing_items):
                            if oi["uuid"] == matched_old_item["uuid"]:
                                existing_items[idx] = data
                                break
                    else:
                        # 徹底沒見過的新公告，發配新 UUID
                        data["uuid"] = str(uuid.uuid4())
                        if "date" not in data or not data["date"]:
                            data["date"] = "1970-01-01"
                        existing_items.append(data)
            except json.JSONDecodeError:
                pass

    # 3. 資料去重與極致排序
    unique_items = {}
    for item in existing_items:
        key = clean_url(item["link"]) or item["title"]
        unique_items[key] = item

    sorted_items = list(unique_items.values())
    sorted_items.sort(key=lambda x: x.get("date", "1970-01-01"), reverse=True)

    # 4. 寫回 JSONL 檔案
    metadata["total_count"] = len(sorted_items)
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        for item in sorted_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"   [成功] {site_name} 整合完畢！總計 {len(sorted_items)} 筆公告。(已完美防禦 429 限流與 UUID 變動)")

def run_parser(site_name, site_html_dir, base_jsonl_dir, config_year=None):
    """
    執行解析。
    注意：因為你移除了 config 的 year，main.py 傳進來的 config_year 會是 None。
    程式會自動啟動內建的當前西元年判定系統。
    """
    html_files = sorted(glob.glob(os.path.join(site_html_dir, "*.html")))
    if not html_files:
        print(f"   [提示] 找不到 {site_html_dir}/ 內的 HTML，略過。")
        return

    os.makedirs(base_jsonl_dir, exist_ok=True)
    ai_jsonl_chunks = []
    
    total_files = len(html_files)
    for index, file_path in enumerate(html_files, start=1):
        print(f"      -> [AI 解析中] 正在處理第 {index}/{total_files} 頁網頁原始碼...")
        result = process_single_html_with_retry(site_name, file_path)
        if result:
            ai_jsonl_chunks.append(result)

    output_file_path = os.path.join(base_jsonl_dir, f"{site_name}.jsonl")
    merge_and_save_jsonl(site_name, ai_jsonl_chunks, output_file_path)
