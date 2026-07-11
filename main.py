import os
import glob
import json
import re
import scraper
import ai_parser
import discord_notifier

def get_config_number(filename):
    # 確保 web1, web2, ..., web10 依數字大小排序
    match = re.search(r'web(\d+)\.json', filename)
    return int(match.group(1)) if match else 0

def main():
    print("啟動自動化整合引擎...\n")
    
    crawler_output_root = "crawler_pages"
    final_results_root = "final_results"
    
    os.makedirs(crawler_output_root, exist_ok=True)
    os.makedirs(final_results_root, exist_ok=True)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    ai_ready = ai_parser.init_ai(api_key)

    # 確保讀取順序為 0, 1, 2...
    config_files = sorted(glob.glob("configs/web*.json"), key=get_config_number)
    
    for config_file in config_files:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        site_name = config.get("site_name", "Unknown_Site")
        custom_year = config.get("year")
        
        print(f"\n{'='*50}\n處理: {site_name} (年份: {custom_year})\n{'='*50}")
        site_html_dir = scraper.run_spider(config, crawler_output_root)

        if ai_ready and site_html_dir:
            ai_parser.run_parser(site_name, site_html_dir, final_results_root, custom_year)
            
    discord_notifier.run_notifier(final_results_root)

if __name__ == "__main__":
    main()
