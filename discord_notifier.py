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

def send_message(webhook_url, site_name, item, display_date):
    title = item.get("title", "無標題公告")
    link = item.get("link", "")
    short_name = item.get("short_name", "校園")
    
    # 如果 display_date 是空字串，就完全不放入這行字
    if display_date:
        description_text = f"\n\n **發布日期：** {display_date}"
    else:
        description_text = ""
    
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
        
        # 判斷是否為第一次啟動
        is_first_run = not os.path.exists(history_file)
        
        sent_combos = []
        if not is_first_run:
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data_loaded = json.load(f)
                    if isinstance(data_loaded, dict):
                        sent_combos = list(data_loaded.keys())
                    elif isinstance(data_loaded, list):
                        sent_combos = data_loaded
            except json.JSONDecodeError:
                pass
                
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
                    
                    if not date_val: continue
                    if date_val != "Nope" and date_val < "2026-01-01": continue
                    
                    base_key = f"{uuid_val}_{date_val}"
                    
                    if base_key not in sent_base_keys:
                        pending_announcements.append((base_key, data))
                        
                except json.JSONDecodeError:
                    pass
        
        # 【修改重點】設計動態的排序邏輯
        def get_sort_key(item):
            date_val = item[1].get("date", "")
            if date_val == "Nope":
                if is_first_run:
                    # 第一次啟動：給 Nope 最小的時間值，強迫排在陣列最前面 (優先發送)
                    return "0000-00-00"
                else:
                    # 第二次往後：把 Nope 當作今天才發布的，和其他今天的新公告排在一起發送
                    return today_date
            return date_val # 正常的日期就直接用字串本身排序
            
        pending_announcements.sort(key=get_sort_key)
        
        new_sent_count = 0
        for base_key, data in pending_announcements:
            date_val = data.get("date", "")
            
            if date_val == "Nope":
                if is_first_run:
                    # 第一次啟動時，不顯示發布日期
                    display_date = ""
                else:
                    # 後續發現新公告時，印上當天發現的時間標籤
                    display_date = today_date
                    
                # 不論第幾次，存入歷史紀錄時一定會帶上 #發現日期
                save_key = f"{base_key}#{today_date}" 
            else:
                display_date = date_val
                save_key = base_key
                
            success = send_message(webhook_url, site_name, data, display_date)
            if success:
                sent_base_keys.add(base_key) 
                sent_combos.append(save_key) # 發送成功後，加入帶有 #標籤 的對照字串
                new_sent_count += 1
                time.sleep(1.5)

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(sorted(sent_combos), f, ensure_ascii=False, indent=4)
            
        if new_sent_count > 0:
            print(f"   [完成] {site_name} 共推送 {new_sent_count} 則新公告，對照表已更新。")
        else:
            print(f"   [完成] {site_name} 目前沒有新公告。")
