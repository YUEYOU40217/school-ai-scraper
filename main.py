import os
import scraper
import ai_parser
import discord_notifier

def main():
    print("啟動自動化整合引擎...\n")
    
    crawler_output_root = "crawler_pages"
    final_results_root = "final_results"
    discord_history_root = "discord_history"
    spiders_root = "spiders"
    
    print("【環境初始化】檢查並建立基礎資料夾結構...")
    os.makedirs(crawler_output_root, exist_ok=True)
    os.makedirs(final_results_root, exist_ok=True)
    os.makedirs(discord_history_root, exist_ok=True)
    print(f"   -> 確認 {crawler_output_root} 存在")
    print(f"   -> 確認 {final_results_root} 存在")
    print(f"   -> 確認 {discord_history_root} 存在")
    
    if os.path.exists(spiders_root):
        print("\n【環境初始化】準備爬蟲輸出子目錄...")
        for item in os.listdir(spiders_root):
            item_path = os.path.join(spiders_root, item)
            
            if os.path.isdir(item_path) and not item.startswith("__"):
                target_dir = os.path.join(crawler_output_root, item)
                
                os.makedirs(target_dir, exist_ok=True)
                print(f"   -> 已建立/確認學校目錄: {target_dir}")
    else:
        print(f"[警告] 找不到 {spiders_root} 資料夾，請確認爬蟲原始檔位置是否正確！")

    print("\n--------------------------------------------------")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    ai_ready = ai_parser.init_ai(api_key)

    print("【第一階段】執行分散式爬蟲...")
    scraped_sites = scraper.run_all_spiders(crawler_output_root)

    if ai_ready and scraped_sites:
        print("\n【第二階段】執行 AI 智慧摘要...")
        for site_name in scraped_sites:
            site_html_dir = os.path.join(crawler_output_root, site_name)
            ai_parser.run_parser(site_name, site_html_dir, final_results_root, "2026")

    print("\n【第三階段】執行 Discord 推播...")
    discord_notifier.run_notifier(final_results_root, discord_history_root)

if __name__ == "__main__":
    main()
