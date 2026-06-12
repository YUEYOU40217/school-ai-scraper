import json
import os
import re
import utils
from google import genai
from urllib.parse import urljoin

# 設定單次處理的最大安全上限（確保整頁能掃完）
MAX_LIMIT = 100 

def format_json_keywords(json_str):
    """將 JSON 字串中的關鍵字陣列縮回單行"""
    pattern = r'"keywords":\s*\[\s*([^\]]*?)\s*\]'
    def replace_func(match):
        items = match.group(1).split('\n')
        cleaned_items = [item.strip() for item in items if item.strip()]
        joined_items = "".join(cleaned_items).replace('","', '", "')
        return f'"keywords": [{joined_items}]'
    return re.sub(pattern, replace_func, json_str, flags=re.DOTALL)

def main():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    target_url = config['urls'][0]
    print(f"鎖定目標網址: {target_url}")
    
    selector_cfg = config.get('selector_config', {})
    row_selector = selector_cfg.get('row_selector', '.mtitle')
    link_selector = selector_cfg.get('link_selector', 'a')
    
    # 1. 抓取網頁原始資料
    source_name, all_links = utils.fetch_links(target_url, row_selector, link_selector)
    
    if not all_links:
        print("警告：抓到的連結數量為 0！")
        return

    # 2. 解析允許的年份範圍
    allowed_years = config.get("allowed_years", [2025, 2026])
    year_keywords = []
    for y in allowed_years:
        year_keywords.append(str(y))          
        year_keywords.append(str(y - 1911))   
    
    print(f"年份範圍過濾：只處理包含 {year_keywords} 的公告條目")

    # 3. 依照日期由新到遠排序
    all_links.sort(key=lambda x: x['date'], reverse=True)

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    processed_data = []
    current_id = 1
    
    # 用來記錄連續遇到非目標年份的計數器
    out_of_range_count = 0 

    # 4. 開始依序檢查並過濾
    for item in all_links[:MAX_LIMIT]:
        # 檢查這條公告是否屬於我們想要的年份
        is_valid_year = any(k in item['row_text'] for k in year_keywords)

        if not is_valid_year:
            out_of_range_count += 1
            print(f"非設定年份範圍，跳過: {item['title']}")
            
            # 💡 智慧省流量中斷機制：
            # 如果連續出現 3 筆以上的舊年份公告，代表已經徹底跨入歷史舊資料區，後面不用再看了。
            if out_of_range_count >= 3:
                print("偵測到已完全進入舊年份歷史資料區，自動停止後續掃描，省下 AI 用量。")
                break
            continue
        
        # 如果是目標年份，計數器歸零（代表還在目標區間內）
        out_of_range_count = 0

        full_url = urljoin(target_url, item['href'])
        print(f"正在請 AI 萃取關鍵字 (ID {current_id}): {item['title']}")
        
        # 呼叫 Gemini 3.1 Flash-Lite
        ai_res = utils.process_ai(item['title'], config['prompt_template'], client)
        
        record = {
            "id": current_id,
            "title": item['title'],
            "link": full_url,
            "keywords": ai_res.get("keywords", [])
        }
        processed_data.append(record)
        current_id += 1

    # 5. 打包大外層 JSON 結構
    output_result = {
        "source_name": source_name,
        "source_link": target_url,
        "data": processed_data
    }

    # 6. 壓縮關鍵字格式並存檔
    raw_json = json.dumps(output_result, ensure_ascii=False, indent=2)
    final_json = format_json_keywords(raw_json)

    with open("announcements.json", "w", encoding="utf-8") as f:
        f.write(final_json)
        
    print(f"成功處理 {len(processed_data)} 筆符合年份範圍的公告關鍵字！")

if __name__ == "__main__":
    main()
