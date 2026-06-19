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
    text = re.sub(r"\n
```$", "", text)
    return text.strip()

def clean_url(url):
    """提取核心網址，確保不受網域或絕對/相對路徑影響"""
    if not url:
        return ""
    url = url.strip()
    match = re.search(r'(/(p|var)/.+)$', url)
    return match.group(1) if match else url

def get_stable_uuid(link, title):
    """
    【核心防護】：產生絕對不變的特徵 UUID
    使用 UUID v5 演算法，只要網址或標題一樣，產生的 UUID 永遠一樣。
    完全不依賴本地歷史檔案，手動啟動也絕不會變動。
    """
    seed = clean_url(link)
    # 如果沒有網址，或者網址太短失去特徵，就退回使用標題作為種子
    if not seed or len(seed) < 5:
        seed = title.strip()
    
    # 加上前綴，確保算出來的指紋不會跟其他系統撞號
    seed = "csu_scraper_" + seed
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

def process_single_html_with_retry(site_name, file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    current_year = datetime.now().year

    prompt = f"""
你是一個嚴格的網頁資料結構化專家。請將以下 HTML 中的「公告/新聞」提取出來，並「嚴格」遵守 JSONL 格式輸出。

【最高指導原則】：
請逐行掃描 HTML 中的表格或清單列表，絕對不可遺漏任何一筆公告。該頁面上有幾筆公告，你就必須輸出幾行 JSON！

【嚴格輸出格式要求】：
1. 絕對不要包含任何 Markdown 標籤。
2. 第一行是來源統計：
{{"source_name": "{site_name}", "source_link": "該網站網址", "total_count": 0}}
3. 第二行開始，每一行代表一個公告。UUID 請留空。請特別注意標題內的雙引號 (") 必須使用反斜線跳脫 (\\")，以免破壞 JSON 格式！
{{"uuid": "", "date": "YYYY-MM-DD", "short_name": "csu", "title": "公告標題", "link": "完整超連結", "keywords": ["字1", "字2", "字3", "字4", "字5"]}}

【重要原則 - 日期 (date) 欄位解析】：
- 必須輸出 YYYY-MM-DD 的西元年格式。
- 若公告僅有月、日而缺少年份，請一律推測為當前西元年份：【 {current_year} 】年。
- 【台灣年份與學期對照表 (嚴格遵守，禁止自行計算)】：
  若為純民國年：112年=2023年，113年=2024年，114年=2025年，115年=2026年，116年=2027年。
  若為學年度：113-1=2024, 113-2=2025, 114-1=2025, 114-2=2026, 115-1=2026, 115-2=2027。

【重要原則 - 關鍵字 (keywords) 欄位解析】：
- 陣列【必須且絕對只能剛好是 5 個元素】。

待處理 HTML：
--- {os.path.basename(file_path)} ---
{html_content}
"""
    if not ai_client:
        return None

    retries = 5
    delay = 4.5
    
    for attempt in range(retries):
        try:
            time.sleep(delay)
            response = ai_client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            return clean_ai_response(response.text)
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                wait_time = 12 * (attempt + 1)
                print(f"      [觸發限流] API 達到每分鐘上限，暫停 {wait_time} 秒後重試...")
                time.sleep(wait_time)
            else:
                print(f"      [錯誤] 呼叫 Gemini 失敗: {e}")
                return None
    return None

def merge_and_save_jsonl(site_name, ai_jsonl_chunks, output_file_path):
    existing_items = {}
    metadata = {"source_name": site_name, "source_link": "", "total_count": 0}

    # 1. 讀取舊資料 (用 UUID 當作字典的金鑰)
    if os.path.exists(output_file_path):
        with open(output_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    if "link" in data and "uuid" in data:
                        existing_items[data["uuid"]] = data
                    elif "source_name" in data:
                        metadata["source_link"] = data.get("source_link", "")
                except json.JSONDecodeError:
                    pass

    # 2. 處理新抓下來的資料
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

                    # 嘗試從舊檔案找相符的紀錄，以保留你已經存在伺服器上的舊版 uuid4
                    matched_uuid = None
                    for old_uuid, old_item in existing_items.items():
                        old_title = old_item.get("title", "").strip()
                        old_clean_link = clean_url(old_item.get("link", ""))
                        if (new_title == old_title) or (new_clean_link and new_clean_link == old_clean_link and len(new_clean_link) > 5):
                            matched_uuid = old_uuid
                            break

                    # 確保關鍵字數量為 5
                    keywords = data.get("keywords", [])
                    if not isinstance(keywords, list): keywords = []
                    keywords = (keywords + ["公告", "資訊", "校園", "最新消息", "無"])[:5]
                    data["keywords"] = keywords

                    if matched_uuid:
                        # 有歷史檔案：繼承舊 UUID 與舊日期
                        data["uuid"] = matched_uuid
                        old_item = existing_items[matched_uuid]
                        if old_item.get("date") and old_item["date"] != "1970-01-01":
                            data["date"] = old_item["date"]
                        if old_item.get("keywords"):
                            data["keywords"] = old_item["keywords"]
                        data["link"] = new_link
                        data["title"] = new_title
                        
                        existing_items[matched_uuid] = data
                    else:
                        # 沒有歷史檔案 (或全新公告)：使用特徵 UUID (絕對不變)
                        data["uuid"] = get_stable_uuid(new_link, new_title)
                        
                        if "date" not in data or not data["date"]:
                            data["date"] = "1970-01-01"
                            
                        existing_items[data["uuid"]] = data
                        
            except json.JSONDecodeError as e:
                print(f"      [警告] 發現 AI 產生了格式錯誤的 JSON，已跳過該筆: {line[:50]}... (原因: {e})")

    # 3. 去重與排序
    unique_items = {item["uuid"]: item for item in existing_items.values()}
    sorted_items = list(unique_items.values())
    sorted_items.sort(key=lambda x: x.get("date", "1970-01-01"), reverse=True)

    metadata["total_count"] = len(sorted_items)
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        for item in sorted_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"   [成功] {site_name} 整合完畢！總計 {len(sorted_items)} 筆公告。(已啟用特徵指紋機制)")

def run_parser(site_name, site_html_dir, base_jsonl_dir, config_year=None):
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
