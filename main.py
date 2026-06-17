import os
import glob
import json
import scraper
import ai_parser

def main():
    print("啟動自動化整合引擎...\n")
    
    # 定義基礎儲存路徑
    base_scrape_dir = "scraped_pages"
    base_jsonl_dir = "formatted_jsonl"
    
    # 初始化 AI 模組
    api_key = os.environ.get("GEMINI_API_KEY")
    ai_ready = ai_parser.init_ai(api_key)
    if not ai_ready:
        print("[警告] 找不到環境變數 GEMINI_API_KEY，將略過 AI 解析，僅執行爬蟲。")

    # 取得所有設定檔
    config_files = sorted(glob.glob("configs/web*.json"))
    if not config_files:
        print("[錯誤] 找不到設定檔，請檢查 configs/ 資料夾。")
        return

    for config_file in config_files:
        with open(config_file, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
            except Exception:
                print(f"[錯誤] 無法解析 JSON 設定檔: {config_file}")
                continue
        
        site_name = config.get("site_name", "Unknown_Site")
        print(f"\n{'='*40}")
        print(f"開始處理專案: {site_name}")
        print(f"{'='*40}")

        # 第一階段：爬蟲下載
        print("\n[階段 1] 執行網頁爬蟲...")
        site_html_dir = scraper.run_spider(config, base_scrape_dir)

        # 第二階段：AI 解析與整合
        if ai_ready and site_html_dir:
            print("\n[階段 2] 執行 AI 內容解析...")
            ai_parser.run_parser(site_name, site_html_dir, base_jsonl_dir)

    print("\n所有自動化任務執行完畢！")

if __name__ == "__main__":
    main()
