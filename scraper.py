import os
import importlib.util
import urllib3
import requests

# 停用不安全連線警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 從環境變數讀取爬蟲專用 API Key
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

# ==============================================================
# 核心工具：連線抓取函數 (這就是剛剛不見的那把鏟子)
# ==============================================================
def fetch_content(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # -------------------------------------------------------------
    # 【API Key 整合邏輯】 (保留你原本的擴充性)
    # -------------------------------------------------------------
    if SCRAPER_API_KEY:
        # 如果需要用 Header 傳遞 API Key，就取消下方註解
        # headers["X-Scraper-API-Key"] = SCRAPER_API_KEY
        pass 
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        response.encoding = response.apparent_encoding
        return response.text
    except Exception as e:
        print(f"      [錯誤] 連線失敗: {e}")
        return None

# ==============================================================
# 爬蟲自動探索引擎
# ==============================================================
def run_all_spiders(base_output_dir):
    spiders_root = "spiders"
    scraped_sites = set()
    
    if not os.path.exists(spiders_root):
        print(f"      [警告] 找不到 {spiders_root} 資料夾，爬蟲終止。")
        return list(scraped_sites)

    # 自動巡邏 spiders 目錄下的所有資料夾與 .py 檔
    for root, dirs, files in os.walk(spiders_root):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                site_name = os.path.basename(root)
                if site_name == "spiders": continue
                
                scraped_sites.add(site_name)
                site_output_dir = os.path.join(base_output_dir, site_name)
                
                script_path = os.path.join(root, file)
                print(f"\n   -> 啟動爬蟲腳本: {site_name} / {file}")
                
                try:
                    # 動態載入 .py 檔
                    spec = importlib.util.spec_from_file_location("spider_module", script_path)
                    spider_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(spider_module)
                    
                    if hasattr(spider_module, "run"):
                        # 呼叫腳本的 run，並把上面定義的 fetch_content 當成工具傳給它
                        spider_module.run(site_output_dir, fetch_content)
                    else:
                        print(f"      [錯誤] {file} 找不到 run() 函數")
                except Exception as e:
                    # 任何腳本內部寫錯或崩潰，都會被這裡攔截
                    print(f"      [錯誤] 執行 {file} 發生崩潰: {e}")

    return list(scraped_sites)
