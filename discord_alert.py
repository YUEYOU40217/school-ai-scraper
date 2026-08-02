import os
import requests

def send_alert(site_name):
    webhook_map = {
        "正修科技大學": os.environ.get("WEBHOOK_ALERT_CSU"),
        "高雄科技大學": os.environ.get("WEBHOOK_ALERT_NKUST"),
    }
    
    webhook_url = webhook_map.get(site_name)
    
    if not webhook_url:
        print(f"      [提醒略過] 找不到 {site_name} 的提醒 Webhook 網址")
        return False

    payload = {
        "content": f"📢 **{site_name} 有新公告！**\n*(詳細內容請至論壇頻道查看最新貼文)*"
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 204:
            print(f"      [提醒成功] 已通知 {site_name} 的一般頻道")
            return True
        else:
            print(f"      [提醒失敗] Discord 回傳代碼: {response.status_code}")
            return False
    except Exception as e:
        print(f"      [提醒錯誤] 連線異常: {e}")
        return False
