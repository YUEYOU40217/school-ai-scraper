import os
import json
import glob
import time
import requests
from datetime import datetime

def get_embed_color(link):
    if not link:
        return 3447003
        
    link_lower = link.lower()
    if "osa.csu.edu.tw" in link_lower:
        return 15105570
    elif "general.csu.edu.tw" in link_lower:
        return 3066993
    elif "academic.csu.edu.tw" in link_lower:
        return 10181046
    elif "nkust.edu.tw" in link_lower:
        return 15158332
        
    return 3447003

# 新增 display_date 參數，用來決定畫面上要顯示的日期
def send_message(webhook_url, site_name, item, display_date):
    title = item.get("title", "無標題公告")
    link = item.get("link", "")
    short_name = item.get("short_name", "校園")
    
    # 使用傳入的 display_date 排版
    description_text = f"\n\n **發布日期：** {display_date}"
    
    payload = {
        "content": f"：嗚、嗚、嗚、嗚！**{site_name} ({short_name}) 有新公告吱！**！！",
        "embeds": [
            {
                "title": title,
                "url": link,
                "description": description_text,
                "color": get_embed_color(link)
            }
        ]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 204:
            return True
        else:
            print(f"      [通知失敗] Discord 回傳代碼: {response.status_code} | 失敗公告: {title} | 網址: {link}")
            return False
    except Exception as e:
        print(f"      [錯誤] Webhook 連線異常: {e} | 失敗公告: {title}")
        return False

def run_notifier(jsonl_dir, history_dir):
    print("\n==================================================")
    print("啟動 Discord 智慧分流推播引擎...")
    print("==================================================")
    
    os.makedirs(history_dir, exist_ok=True)
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    webhook_map = {
        "正修科技大學": os.environ.get("WEBHOOK_CSU"),
        "國立高雄科技大學": os.environ.get("WEBHOOK_NKUST"),
    }

    jsonl_files = glob.glob(os.path.join(jsonl_dir, "*.jsonl"))
    for file_path in jsonl_files:
        site_name = os.path.basename(file_path).replace(".jsonl", "")
        print(f"   -> 正在檢查: {site_name}")
        
        webhook_url = webhook_map.get(site_name)
        if not webhook_url:
            print(f"      [提示] 找不到 {site_name} 對應的 Webhook 網址，跳過推播。")
            continue
            
        history_file = os.path.join(history_dir, f"{site_name}_history.json")
        
        # 1. 讀取歷史檔案的原始字串列表
        sent_combos = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data_loaded = json.load(f)
                    if isinstance(data_loaded, dict):
                        sent_combos = list(data_loaded.keys())
                    elif isinstance(data_loaded, list):
                        sent_combos = data_loaded
            except json.JSONDecodeError:
                pass
                
        # 2. 建立「基礎對照集合」：把 # 後面的發現時間切掉，只留 {uuid}_{date} 用來比對
        # 例如: "011114ce..._Nope#2026-07-24" 會變成 "011114ce..._Nope"
        sent_base_keys = set([combo.split("#")[0] for combo in sent_combos])
        
        pending_announcements = []
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    if "total_count" in data: continue
                    
                    date_val = data.get("date", "")
                    uuid_val = data.get("uuid", "")
                    
                    # 嚴格過濾時間
                    if not date_val: continue
                    if date_val != "Nope" and date_val < "2026-01-01": continue
                    
                    # 這是原始資料的 Key (如: uuid_2026-04-10 或 uuid_Nope)
                    base_key = f"{uuid_val}_{date_val}"
                    
                    # 3. 使用切掉 # 的基礎 Key 來判斷是否已經發送過
                    if base_key not in sent_base_keys:
                        pending_announcements.append((base_key, data))
                        
                except json.JSONDecodeError:
                    pass
        
        # 由舊到新排序確保時間軸合理
        pending_announcements.sort(key=lambda x: x[1].get("date", "2026-01-01"))
        
        new_sent_count = 0
        for base_key, data in pending_announcements:
            date_val = data.get("date", "")
            
            # 4. 針對 Nope 處理顯示日期與儲存的 Key
            if date_val == "Nope":
                display_date = today_date
                save_key = f"{base_key}#{today_date}" # 加上發現時間的標記
            else:
                display_date = date_val
                save_key = base_key # 正常日期的就保持原樣
                
            success = send_message(webhook_url, site_name, data, display_date)
            if success:
                # 同步更新集合與列表
                sent_base_keys.add(base_key) 
                sent_combos.append(save_key)
                new_sent_count += 1
                time.sleep(1.5)

        # 覆蓋寫入最新的對照表 (包含帶有 # 標記的完整字串)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(sorted(sent_combos), f, ensure_ascii=False, indent=4)
            
        if new_sent_count > 0:
            print(f"   [完成] {site_name} 共推送 {new_sent_count} 則新公告，對照表已更新。")
        else:
            print(f"   [完成] {site_name} 目前沒有新公告。")
