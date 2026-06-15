import os
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from google import genai
from utils import fetch_html_text, process_ai_batch

def parse_html_to_links(html_text, target_url):
    """解析 HTML 並萃取深度達 6 層的公告與日期"""
    if not html_text:
        return "未命名網頁", []
        
    soup = BeautifulSoup(html_text, "html.parser")
    source_name = soup.title.get_text(strip=True) if soup.title else "未命名網頁"
    links = []
    
    all_a_tags = soup.find_all('a')
    garbage_words = ["跳到", "主要內容", "previous", "next", "首頁", "返回", "coreui"]
    
    for a_tag in all_a_tags:
        href = a_tag.get('href')
        title = a_tag.get_text(strip=True)
        
        if not href or not title or len(title) < 5: 
            continue
            
        if href.startswith('#') or any(w in title.lower() for w in garbage_words):
            continue
            
        full_url = urljoin(target_url, href)
        parent = a_tag.parent
        row_text = ""
        date_str = "0000-00-00"
        
        # 深度探索：往上找 6 層以捕捉置頂公告或複雜結構的日期
        for _ in range(6):
            if parent:
                row_text = parent.get_text(separator=' ', strip=True)
                date_match = re.search(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})', row_text)
                if date_match:
                    date_str = date_match.group(1)
                    break
                parent = parent.parent
        
        if date_str == "0000-00-00":
            continue
            
        links.append({
            "title": title, 
            "href": full_url, 
            "row_text": row_text,
            "date": date_str
        })
        
    return source_name, links

def get_links_with_dynamic_fallback(target_url):
    """取得連結，若靜態失敗則自動啟動 DrissionPage 補救"""
    html_text = fetch_html_text(target_url)
    source_name, links = parse_html_to_links(html_text, target_url)
    
    # 【動態補救防線】
    if not links:
        print(f"[靜態未取得有效內容] 啟動 DrissionPage 自動化瀏覽器強行突破: {target_url}")
        try:
            from DrissionPage import ChromiumPage, ChromiumOptions
            co = ChromiumOptions().auto_port()
            co.headless(True)
            page = ChromiumPage(co)
            page.get(target_url)
            page.wait.ele_loaded('tag:a', timeout=10)
            page.wait(2)
            dynamic_html = page.html
            page.quit()
            
            source_name, links = parse_html_to_links(dynamic_html, target_url)
            print("[動態補救] 成功取得渲染後的網頁原始碼。")
        except Exception as e:
            print(f"[動態補救異常] 錯誤: {e}")
            
    return source_name, links

def main():
    # 這裡放你要爬取的學校網址清單
    target_urls = [
        "https://www.csu.edu.tw/p/403-1000-13-1.php?Lang=zh-tw"
        # 可以加入其他網址
    ]
    
    all_raw_data = {}
    
    # 階段 1：執行爬蟲並儲存原始狀態
    print("=== 階段 1：開始執行爬蟲 ===")
    for url in target_urls:
        source_name, links = get_links_with_dynamic_fallback(url)
        all_raw_data[source_name] = links
        print(f"[{source_name}] 成功抓取 {len(links)} 筆原始公告。")
        
    # 【輸出除錯檢查點】將原始資料存成 JSON，不會進到 AI 階段
    debug_filename = "raw_scraped_data.json"
    with open(debug_filename, 'w', encoding='utf-8') as f:
        json.dump(all_raw_data, f, ensure_ascii=False, indent=4)
    print(f"\n[檢查點] 爬蟲取得的原始資料已儲存至 '{debug_filename}'。")
    print("請開啟該檔案檢查內容是否正確包含 15 筆公告。確認無誤後，再將資料傳給 AI 進行後續處理。")

    # 階段 2：AI 解析 (暫時註解，待你確認原始資料正確後再開啟)
    """
    print("\n=== 階段 2：啟動 AI 解析 ===")
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    prompt_template = "請從以下公告標題萃取關鍵字：\n{batch_input}" # 請替換為你真實的 template
    
    final_results = []
    for source, links in all_raw_data.items():
        titles = [item['title'] for item in links]
        # 假設每 20 筆批次處理... (放入你原本的批次處理邏輯)
        ai_parsed_data = process_ai_batch(titles, prompt_template, client)
        
        for i, link_data in enumerate(links):
            if i < len(ai_parsed_data):
                link_data['keywords'] = ai_parsed_data[i].get('keywords', [])
            final_results.append(link_data)
            
    with open('announcements.json', 'w', encoding='utf-8') as f:
         json.dump(final_results, f, ensure_ascii=False, indent=4)
    print("全部處理完畢，已寫入 announcements.json")
    """

if __name__ == "__main__":
    main()
