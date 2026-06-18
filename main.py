import os
import glob
import json
import scraper
import ai_parser

def main():
    print("啟動自動化整合引擎...\n")
    
    # 1. 定義明確的資料夾路徑
    crawler_output_root = "crawler_pages"   
    final_results_root = "final_results"     
    
    # 2. 自動建立暫存與最終成果的根資料夾
    os.makedirs(crawler_output_root, exist_ok=True)
    os.makedirs(final_results_root, exist_ok=True)
    print(f"[系統初始化] 已自動建立/確認必要資料夾：")
    print(f"  -> 暫存資料夾: {crawler_output_root}/")
    print(f"  -> 最終成果資料夾: {final_results_root}/\n")
    
    # 初始化 AI 模組並檢查 API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    ai_ready = ai_parser.init_ai(api_key)
    if not ai_ready:
        print("[警告] 找不到環境變數 GEMINI_API_KEY，將略過 AI 解析，僅執行爬蟲。")

    # 取得所有網站的設定檔
    config_files = sorted(glob.glob("configs/web*.json"))
    if not config_files:
        print("[錯誤] 找不到設定檔，請檢查 configs/ 資料夾是否存在。")
        return

    for config_file in config_files:
        with open(config_file, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
            except Exception:
                print(f"[錯誤] 無法解析 JSON 設定檔: {config_file}")
                continue
        
        site_name = config.get("site_name", "Unknown_Site")
        custom_year = config.get("year")
        
        print(f"\n{'='*50}")
        print(f"開始處理專案: {site_name}")
        if custom_year:
            print(f"[載入設定] 已指定基準年份: {custom_year}")
        print(f"{'='*50}")

        # 【步驟一】執行網頁爬蟲
        print("\n[功能 1] 執行網頁爬蟲下載...")
        site_html_dir = scraper.run_spider(config, crawler_output_root)

        # 【步驟二】執行 AI 摘要
        if ai_ready and site_html_dir:
            print("\n[功能 2] 讀取爬蟲資料夾，執行 AI 內容摘要...")
            ai_parser.run_parser(site_name, site_html_dir, final_results_root, custom_year)

    print("\n所有任務執行完畢！")

if __name__ == "__main__":
    main()
