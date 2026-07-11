import os
import json
import glob
import time
import requests

def get_embed_color(link):
    """根據網址特徵動態判斷處室，並回傳對應的十進位顏色代碼"""
    if not link:
        return 3447003  # 預設藍色
        
    link_lower = link.lower()
    
    # 依網址內包含的處室關鍵字進行顏色分流
    if "osa.csu.edu.tw" in link_lower:
        return 15105570  # 學務處：亮橘色 (#E67E22)
    elif "general.csu.edu.tw" in link_lower:
        return 3066993   # 總務處：翠綠色 (#2ECC71)
    elif "academic.csu.edu.tw" in link_lower:
        return 10181046  # 教務處：魅惑紫 (#9B59B6)
    elif "nkust.edu.tw" in link_lower:
        return 15158332  # 高科大最新消息：烈焰紅 (#E74C3C)
        
    return 3447003      # 正修全部公告 / 其他預設：經典藍 (#3498DB)

def send_message(webhook_url, site_name, item):
    """將單筆公告轉換為 Discord Embed 格式並發送"""
    title = item.get("title", "無標題公告")
    link = item.get("link", "")
    date = item.get("date", "未知日期")
    keywords = item.get("keywords", [])
    
    # 格式化關鍵字陣列為字串
    keywords_str = ", ".join(keywords) if keywords else "無"
    
    # 動態獲取該處室對應的顏色
    embed_color = get_embed_color(link)
    
    # 組合 Discord 訊息內容
    payload = {
        "content": "🐵：嗚、嗚、嗚、嗚！!!新消息！！",
        "embeds": [
            {
                "title": title,
                "url": link,
                "description": f"發布日期：{date}\n關鍵字：{keywords_str}",
                "color": embed_color  # 使用動態分配的顏色
            }
        ]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 204:
            print(f"      [通知成功] 已推播: {title}")
            return True
        else:
            print(f"      [通知失敗] Discord 回傳代碼: {response.status_code}")
            return False
    except Exception as e:
        print(f"      [錯誤] Webhook 連線異常: {e}")
        return False

def run_notifier(jsonl_dir):
    print("\n==================================================")
    print("啟動 Discord 推播引擎...")
    print("==================================================")
    
    webhook_map = {
        "正修科技大學": os.environ.get("WEBHOOK_CSU"),
        "國立高雄科技大學": os.environ.get("WEBHOOK_NKUST"),
    }

    # 讀取推播歷史紀錄檔（uuid_date 組合）
    history_file = os.path.join(jsonl_dir, "discord_history.json")
    sent_combos = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                sent_combos = json.load(f)
        except json.JSONDecodeError:
            pass
            
    sent_set = set(sent_combos)
    new_sent_count = 0
    
    jsonl_files = glob.glob(os.path.join(jsonl_dir, "*.jsonl"))
    for file_path in jsonl_files:
        site_name = os.path.basename(file_path).replace(".jsonl", "")
        print(f"   -> 正在檢查: {site_name}")
        
        webhook_url = webhook_map.get(site_name)
        if not webhook_url:
            print(f"      [提示] 找不到 {site_name} 對應的 Webhook 網址，跳過推播。")
            continue
        
        pending_announcements = []
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    if "total_count" in data: continue
                    
                    date_val = data.get("date", "")
                    uuid_val = data.get("uuid", "")
                    
                    # 1. 嚴格過濾：只保留 2026 年（含）之後的公告
                    if not date_val or date_val < "2026-01-01":
                        continue
                    
                    # 2. 建立 UUID 與日期的唯一識別組合
                    combo_key = f"{uuid_val}_{date_val}"
                    
                    if combo_key not in sent_set:
                        pending_announcements.append((combo_key, data))
                        
                except json.JSONDecodeError:
                    pass
        
        # 3. 將待發送清單依日期由舊到新排序
        pending_announcements.sort(key=lambda x: x[1].get("date", "2026-01-01"))
        
        # 4. 依序執行推播發送
        for combo_key, data in pending_announcements:
            success = send_message(webhook_url, site_name, data)
            if success:
                sent_set.add(combo_key)
                new_sent_count += 1
                time.sleep(1.5)

    if new_sent_count > 0:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(list(sent_set), f, ensure_ascii=False)
        print(f"   [完成] 本次共推送 {new_sent_count} 則新公告，已更新紀錄檔。")
    else:
        print("   [完成] 目前沒有新公告需要推播。")
