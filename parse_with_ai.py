import os
import glob
import json
import re
import uuid
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-1.5-flash"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def clean_ai_response(text):
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text.strip()

def process_html_with_ai(site_name, html_files, batch_index):
    print(f"      -> 正在請 AI 解析第 {batch_index} 組 ({len(html_files)} 個 HTML 檔案)...")
    
    combined_html_content = ""
    for file_path in html_files:
        with open(file_path, "r", encoding="utf-8") as f:
            combined_html_content += f"\n\n--- {os.path.basename(file_path)} ---\n"
            combined_html_content += f.read()

    prompt = f"""
你是一個嚴格的網頁資料結構化專家。請將以下 HTML 中的「公告/新聞」提取出來，並「嚴格」遵守 JSONL 格式輸出。

【嚴格輸出格式要求】：
1. 絕對不要包含任何 Markdown 標籤 (例如不要寫 ```jsonl)。
2. 第一行是來源統計：
{{"source_name": "{site_name}", "source_link": "該網站網址", "total_count": 0}}
3. 第二行開始，每一行代表一個公告。UUID 請留空。
{{"uuid": "", "short_name": "csu", "title": "公告標題", "link": "完整超連結", "keywords": ["字1", "字2", "字3", "字4", "字5"]}}

【重要原則】：
- keywords 陣列【必須剛好是 5 個元素】。
- 只提取核心公告，過濾掉導覽列等雜訊。

待處理 HTML：
{combined_html_content}
"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return clean_ai_response(response.text)
    except Exception as e:
        print(f"      [錯誤] 呼叫 Gemini 失敗: {e}")
        return None

def merge_and_save_jsonl(site_name, ai_jsonl_chunks, output_file_path):
    existing_items = {}
    metadata = {"source_name": site_name, "source_link": "", "total_count": 0}

    # 1. 讀取舊資料：用 URL (link) 當作鑰匙，把舊的 UUID 鎖死背起來
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
                    
                    # 【強制 5 個關鍵字邏輯】
                    keywords = data.get("keywords", [])
                    if not isinstance(keywords, list): keywords = []
                    # 數量不夠用預設詞補滿，數量超過直接切斷，確保絕對是 5 個
                    keywords = (keywords + ["公告", "資訊", "校園", "最新消息", "無"])[:5]
                    data["keywords"] = keywords

                    # 【UUID 鎖定與新增邏輯】
                    if link in existing_items:
                        # 舊公告：強制繼承原本的 UUID
                        data["uuid"] = existing_items[link]["uuid"]
                    else:
                        # 新公告：配發全新 UUID
                        data["uuid"] = str(uuid.uuid4())
                        new_items_count += 1
                    
                    # 更新至字典 (以新蓋舊，但 UUID 已經被我們保留了)
                    existing_items[link] = data
            except json.JSONDecodeError:
                pass

    # 3. 寫回 JSONL 檔案
    metadata["total_count"] = len(existing_items)
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        # 為了穩定，我們可以依照網址排序寫入
        for link in sorted(existing_items.keys()):
            f.write(json.dumps(existing_items[link], ensure_ascii=False) + "\n")
            
    print(f"   [成功] {site_name} 整理完畢！本次新增 {new_items_count} 筆，目前總計 {len(existing_items)} 筆公告。")

def main():
    if not GEMINI_API_KEY:
        print("[警告] 找不到環境變數 GEMINI_API_KEY，略過 AI 處理。")
        return

    output_dir = "formatted_jsonl"
    os.makedirs(output_dir, exist_ok=True)
    
    config_files = sorted(glob.glob("configs/web*.json"))
    for config_file in config_files:
        with open(config_file, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
            except:
                continue
                
        site_name = config.get("site_name", "Unknown_Site")
        print(f"\n[AI 開始處理] 目標任務: {site_name}")
        
        # 精準對應 main.py 儲存的路徑
        site_html_dir = os.path.join("scraped_pages", site_name)
        html_files = sorted(glob.glob(os.path.join(site_html_dir, "*.html")))
        
        if not html_files:
            print(f"   [提示] 找不到 {site_html_dir}/ 內的 HTML，略過。")
            continue

        batches = list(chunk_list(html_files, 10))
        ai_jsonl_chunks = []
        
        for index, batch in enumerate(batches, start=1):
            result = process_html_with_ai(site_name, batch, index)
            if result:
                ai_jsonl_chunks.append(result)

        output_file_path = os.path.join(output_dir, f"{site_name}.jsonl")
        merge_and_save_jsonl(site_name, ai_jsonl_chunks, output_file_path)

if __name__ == "__main__":
    main()
