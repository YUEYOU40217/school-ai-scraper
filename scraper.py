import os
import json
import requests
import urllib3

# 關閉 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_raw_html(url):
    """一字不漏地抓取網頁最原始的 HTML 原始碼"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        # 自動偵測網頁編碼，防止中文亂碼
        response.encoding = response.apparent_encoding
        return response.text
    except Exception as e:
        print(f"連線異常: {e}")
        return None

def main():
    print("啟動【100% 原始碼全量無損抓取】管線...")
    target_url = "https://www.csu.edu.tw/p/403-1000-13-1.php?Lang=zh-tw"
    
    # 抓取網頁原始碼（這裡面包含所有的 HTML、JavaScript、CSS、文字）
    raw_html_content = fetch_raw_html(target_url)
    
    if not raw_html_content:
        print("無法載入目標網頁，終止執行。")
        return

    # 建立符合 GitHub Actions 部署要求的 public 目錄
    output_folder = "public"
    os.makedirs(output_folder, exist_ok=True)
    
    # ----------------------------------------------------
    # 輸出檔案 1：把整個原始碼塞進 JSON 的一個欄位裡
    # ----------------------------------------------------
    json_file_path = os.path.join(output_folder, "data.json")
    payload = {
        "site_name": "正修科技大學網頁全量備份",
        "url": target_url,
        "full_html_source": raw_html_content  # 整個網頁原始碼都在這個欄位裡
    }
    
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=4)
        
    # ----------------------------------------------------
    # 輸出檔案 2：直接存成一個標準的 .html 檔案（選備，方便你直接看原始碼）
    # ----------------------------------------------------
    html_file_path = os.path.join(output_folder, "source.html")
    with open(html_file_path, "w", encoding="utf-8") as html_file:
        html_file.write(raw_html_content)
        
    print("任務完成！")
    print(f"1. 全量 JSON 檔已寫入: {json_file_path}")
    print(f"2. 原始網頁網頁檔已寫入: {html_file_path}")

if __name__ == "__main__":
    main()
