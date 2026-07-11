import os
import json
import glob
import time
import requests

def send_message(webhook_url, site_name, item):
    """將單筆公告轉換為 Discord Embed 格式並發送"""
    title = item.get("title", "無標題公告")
    link = item.get("link", "")
    date = item.get("date", "未知日期")
    short_name = item.get("short_name", "校園")
    
    # 組合 Discord Embed 規格
    payload = {
        "content": f"📢 **{site_name} ({short_name}) 有新公告囉！**",
        "embeds": [
            {
                "title": title,
                "url": link,
                "description": f"發布日期：{date}",
                "color": 3447003  # 側邊條顏色（十進位藍色）
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
    print("啟動 Discord 智慧分流推播引擎...")
    print("==================================================")
    
    # 對應表：左邊的名稱必須與 configs 內設定的 site_name（即產出的 jsonl 檔名）完全一致
    webhook_map = {
        "正修科技大學": os.environ.get("WEBHOOK_CSU"),
        "國立高雄科技大學": os.environ.get("WEBHOOK_NKUST"),
        # 未來有新學校，直接在下方依樣畫葫蘆增加即可
        # "學校名稱": os.environ.get("環境變數名稱")
    }

    # 讀取推播歷史紀錄，避免重複發送
    history_file = os.path.join(jsonl_dir, "discord_history.json")
    sent_uuids = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                sent_uuids = json.load(f)
        except json.JSONDecodeError:
            pass
            
    sent_set = set(sent_uuids)
    new_sent_count = 0
    
    # 掃描 final_results 內所有的 jsonl 檔案
    jsonl_files = glob.glob(os.path.join(jsonl_dir, "*.jsonl"))
    for file_path in jsonl_files:
        # 從檔名還原學校名稱（例如："正修科技大學.jsonl" -> "正修科技大學"）
        site_name = os.path.basename(file_path).replace(".jsonl", "")
        print(f"   -> 正在檢查: {site_name}")
        
        # 取得該學校對應的 Webhook 網址
        webhook_url = webhook_map.get(site_name)
        if not webhook_url:
            print(f"      [提示] 找不到 {site_name} 對應的 Webhook 網址，跳過推播。")
            continue
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    # 跳過第一行的 metadata 統計資料
                    if "total_count" in data: continue
                    
                    uuid_val = data.get("uuid")
                    # 如果這筆公告的 UUID 沒發送過，就進行推播
                    if uuid_val and uuid_val not in sent_set:
                        success = send_message(webhook_url, site_name, data)
                        if success:
                            sent_set.add(uuid_val)
                            new_sent_count += 1
                            # 稍作延遲，避免觸發 Discord 速率限制
                            time.sleep(1.5)
                            
                except json.JSONDecodeError:
                    pass

    # 如果有新發送的公告，更新歷史紀錄檔
    if new_sent_count > 0:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(list(sent_set), f, ensure_ascii=False)
        print(f"   [完成] 本次共推送 {new_sent_count} 則新公告，已更新紀錄檔。")
    else:
        print("   [完成] 目前沒有新公告需要推播。")
