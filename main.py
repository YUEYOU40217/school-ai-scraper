import os
import scraper
import ai_parser
import discord_notifier

def main():
    print("啟動自動化整合引擎...\n")
    
    crawler_output_root = "crawler_pages"
    final_results_root = "final_results"
    discord_history_root = "discord_history"
    
    os.makedirs(final_results_root, exist_ok=True)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    ai_ready = ai_parser.init_ai(api_key)

    print("【第一階段】執行分散式爬蟲...")
    
    scraped_sites = scraper.run_all_spiders(crawler_output_root)

    if ai_ready and scraped_sites:
        print("【第二階段】執行 AI 智慧摘要...")
        for site_name in scraped_sites:
            site_html_dir = os.path.join(crawler_output_root, site_name)
            ai_parser.run_parser(site_name, site_html_dir, final_results_root, "2026")

    print("【第三階段】執行 Discord 推播...")
    discord_notifier.run_notifier(final_results_root, discord_history_root)

if __name__ == "__main__":
    main()
