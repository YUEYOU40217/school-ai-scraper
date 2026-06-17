import os
import glob
import json
import scraper
import ai_parser

def main():
    print("啟動自動化整合引擎...\n")
    
    # 1. 定義明確的資料夾路徑
    crawler_output_root = "crawler_pages"   # 爬蟲爬完後的暫存資料夾
    final_results_root = "final_results"     # 最終成果的資料夾
    
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
        print(f"\n{'='*50}")
        print(f"開始處理專案: {site_name}")
        print(f"{'='*50}")

        # 【步驟一】執行網頁爬蟲 -> 資料會存到 crawler_pages/網站名稱/ 
        print("\n[功能 1] 執行網頁爬蟲下載...")
        site_html_dir = scraper.run_spider(config, crawler_output_root)

        # 【步驟二】執行 AI 摘要 -> 從 site_html_dir 取資料，結果存到 final_results/
        if ai_ready and site_html_dir:
            print("\n[功能 2] 讀取爬蟲資料夾，執行 AI 內容摘要...")
            ai_parser.run_parser(site_name, site_html_dir, final_results_root)

    print("\n所有 HTML 下載與 AI 摘要任務執行完畢！")

if __name__ == "__main__":
    main()
