import os
import json
import glob
import time
import requests

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

def send_message(webhook_url, site_name, item):
    title = item.get("title", "無標題公告")
    link = item.get("link", "")
    date = item.get("date", "未知日期")
    short_name = item.get("short_name", "校園")
    
    # 移除關鍵字，僅保留發布日期
    description_text = f"📅 **發布日期：** {date}"
    
    payload = {
        "content": f"🐵：嗚、嗚、嗚、嗚！**{site_name} ({short_name}) 有新公告吱！**！！",
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
            # 加入 title 與 link，方便你抓出是哪一條導致 400 錯誤
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
                
        sent_set = set(sent_combos)
        pending_announcements = []
        new_sent_count = 0
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    if "total_count" in data: continue
                    
                    date_val = data.get("date", "")
                    uuid_val = data.get("uuid", "")
                    
                    if not date_val or date_val < "2026-01-01":
                        continue
                    
                    combo_key = f"{uuid_val}_{date_val}"
                    
                    if combo_key not in sent_set:
                        pending_announcements.append((combo_key, data))
                        
                except json.JSONDecodeError:
                    pass
        
        pending_announcements.sort(key=lambda x: x[1].get("date", "2026-01-01"))
        
        for combo_key, data in pending_announcements:
            success = send_message(webhook_url, site_name, data)
            if success:
                sent_set.add(combo_key)
                new_sent_count += 1
                time.sleep(1.5)

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(sorted(list(sent_set)), f, ensure_ascii=False, indent=4)
            
        if new_sent_count > 0:
            print(f"   [完成] {site_name} 共推送 {new_sent_count} 則新公告，對照表已更新。")
        else:
            print(f"   [完成] {site_name} 目前沒有新公告。")
