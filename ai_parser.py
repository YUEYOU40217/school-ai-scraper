import os
import glob
import json
import re
import uuid
from google import genai

# 使用最新且經濟的 3.1 Flash-Lite 模型
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

def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def clean_ai_response(text):
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text.strip()

def process_html_with_ai(site_name, html_files, batch_index, config_year):
    print(f"      -> 正在請 AI 解析第 {batch_index} 組 ({len(html_files)} 個 HTML 檔案)...")
    
    combined_html_content = ""
    for file_path in html_files:
        with open(file_path, "r", encoding="utf-8") as f:
            combined_html_content += f"\n\n--- {os.path.basename(file_path)} ---\n"
            combined_html_content += f.read()

    # 判斷是否由使用者指定了年份，動態調整規則
    year_instruction = "若公告僅有月、日而缺少年份，請合理推測為當前年份。"
    if config_year:
        year_instruction = f"【強制基準年份】：設定檔已指定年份為「{config_year}」，若公告僅有月、日缺少年份，請一律強制補上西元 {config_year} 年！"

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
- 【台灣學年度推算公式】：
  若出現「N學年度-1 (上學期)」，西元年為 N + 1911。
  若出現「N學年度-2 (下學期)」，西元年為 N + 1911 + 1。
  (例如：114-1 為 2025 年；114-2 為 2026 年；115-1 為 2026 年)。
- 若標示純民國年(如113年)，請加1911轉換為西元年。
- {year_instruction}

【重要原則 - 關鍵字 (keywords) 欄位解析】：
- 陣列【必須且絕對只能剛好是 5 個元素】。請從公告內文中精粹出最具代表性的五個詞彙。
- 只提取核心公告，過濾掉選單、導覽列等無關雜訊。

待處理 HTML：
{combined_html_content}
"""
    if not ai_client:
        print("      [錯誤] AI 用戶端尚未成功初始化。")
        return None

    try:
        response = ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return clean_ai_response(response.text)
    except Exception as e:
        print(f"      [錯誤] 呼叫 Gemini 失敗: {e}")
        return None

def merge_and_save_jsonl(site_name, ai_jsonl_chunks, output_file_path):
    existing_items = {}
    metadata = {"source_name": site_name, "source_link": "", "total_count": 0}

    # 1. 讀取舊資料：保留舊公告的 UUID
    if os.path.exists(output_file_path):
        with open(output_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    if "link" in data and "uuid" in data:
                        existing_items[data["link"]] = data
                    elif "source_name" in data:
                        metadata["source_link"] = data.get("source_link", "")
                except json.JSONDecodeError:
                    pass

    # 2. 處理 AI 新抓出來的資料
    new_items_count = 0
    for chunk in ai_jsonl_chunks:
        if not chunk: continue
        for line in chunk.split("\n"):
            if not line.strip(): continue
            try:
                data = json.loads(line)
                
                if "source_name" in data and not metadata["source_link"]:
                    metadata["source_link"] = data.get("source_link", "")
                elif "link" in data:
                    link = data["link"]
                    
                    # 雙重保險：確保關鍵字絕對是 5 個
                    keywords = data.get("keywords", [])
                    if not isinstance(keywords, list): keywords = []
                    keywords = (keywords + ["公告", "資訊", "校園", "最新消息", "無"])[:5]
                    data["keywords"] = keywords

                    # 確保有 date 欄位，若 AI 漏掉則給極小值預設值
                    if "date" not in data or not data["date"]:
                        data["date"] = "1970-01-01"

                    # UUID 鎖定與新增邏輯
                    if link in existing_items:
                        data["uuid"] = existing_items[link]["uuid"]
                    else:
                        data["uuid"] = str(uuid.uuid4())
                        new_items_count += 1
                    
                    existing_items[link] = data
            except json.JSONDecodeError:
                pass

    # 3. 將資料轉換為列表並【依日期由大到小排序】
    sorted_items = list(existing_items.values())
    sorted_items.sort(key=lambda x: x.get("date", "1970-01-01"), reverse=True)

    # 4. 寫回 JSONL 檔案
    metadata["total_count"] = len(sorted_items)
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        for item in sorted_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"   [成功] {site_name} 整理完畢！本次新增 {new_items_count} 筆，目前總計 {len(sorted_items)} 筆公告 (已依日期由新到舊排序)。")

def run_parser(site_name, site_html_dir, base_jsonl_dir, config_year=None):
    html_files = sorted(glob.glob(os.path.join(site_html_dir, "*.html")))
    
    if not html_files:
        print(f"   [提示] 找不到 {site_html_dir}/ 內的 HTML，略過。")
        return

    os.makedirs(base_jsonl_dir, exist_ok=True)
    batches = list(chunk_list(html_files, 10))
    ai_jsonl_chunks = []
    
    for index, batch in enumerate(batches, start=1):
        result = process_html_with_ai(site_name, batch, index, config_year)
        if result:
            ai_jsonl_chunks.append(result)

    output_file_path = os.path.join(base_jsonl_dir, f"{site_name}.jsonl")
    merge_and_save_jsonl(site_name, ai_jsonl_chunks, output_file_path)
