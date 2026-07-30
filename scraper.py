import os
import importlib.util
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

def fetch_content(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    if SCRAPER_API_KEY:
        pass 

    try:
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        response.encoding = response.apparent_encoding
        return response.text
    except Exception as e:
        print(f"      [錯誤] 連線失敗: {e}")
        return None

def run_all_spiders(base_output_dir):
    spiders_root = "spiders"
    scraped_sites = set()

    if not os.path.exists(spiders_root):
        print(f"      [警告] 找不到 {spiders_root} 資料夾，爬蟲終止。")
        return list(scraped_sites)

    for root, dirs, files in os.walk(spiders_root):
        for file in files:
            # 這裡新增了 not file.startswith("~") 的判斷
            if file.endswith(".py") and not file.startswith("__") and not file.startswith("~"):
                site_name = os.path.basename(root)
                if site_name == "spiders": continue

                scraped_sites.add(site_name)
                site_output_dir = os.path.join(base_output_dir, site_name)

                script_path = os.path.join(root, file)
                print(f"\n   -> 啟動爬蟲腳本: {site_name} / {file}")

                try:
                    spec = importlib.util.spec_from_file_location("spider_module", script_path)
                    spider_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(spider_module)

                    if hasattr(spider_module, "run"):
                        spider_module.run(site_output_dir, fetch_content)
                    else:
                        print(f"      [錯誤] {file} 找不到 run() 函數")
                except Exception as e:
                    print(f"      [錯誤] 執行 {file} 發生崩潰: {e}")

    return list(scraped_sites)
