import os
import json
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ========================================================
# 1. 創立具備重試機制的 requests Session (供抓取內文使用)
# ========================================================
def get_robust_session():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    return session

# ========================================================
# 2. 【新版】使用 Playwright 動態網頁自動翻頁爬蟲 (抓取連結)
# ========================================================
def fetch_links_smart(url, max_pages=3):
    """使用 Playwright 真實瀏覽器抓取目標網頁，並自動翻頁"""
    print(f"🔍 啟動 Playwright 瀏覽器準備抓取: {url}")
    
    links_data = []
    source_name = "未知網頁"
    
    # 啟動 Playwright
    with sync_playwright() as p:
        # 在 GitHub Actions 上必須設為 headless=True (背景執行)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url)
            # 等待網頁初始載入完成
            page.wait_for_load_state('networkidle')
            
            source_name = page.title()
            ignore_keywords = ["首頁", "english", "在校生", "家長", "校友", "行事曆", "聯絡我們", "繁體", "简体"]

            # 自動翻頁迴圈
            for current_page in range(1, max_pages + 1):
                print(f"   📄 正在解析第 {current_page} 頁...")
                
                # 取得當前網頁渲染後的完整 HTML
                html_content = page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 解析連結
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href'].strip()
                    if href.startswith(('javascript:', 'mailto:', 'tel:', '#')): continue
                    
                    link_text = a_tag.get_text(strip=True) or a_tag.get('title', '').strip()
                    if len(link_text) <= 2: continue
                    if any(keyword in link_text.lower() for keyword in ignore_keywords): continue

                    full_url = urljoin(url, href)
                    parent = a_tag.parent
                    list_context = parent.get_text(separator=' ', strip=True) if parent else ""

                    # 避免重複抓取相同的公告
                    if not any(d['href'] == full_url for d in links_data):
                        links_data.append({
                            "title": link_text,
                            "href": full_url,
                            "list_context": list_context
                        })
                
                # 如果還沒到最後一頁，嘗試點擊「下一頁」
                if current_page < max_pages:
                    try:
                        # 尋找包含「下一頁」或「>」的按鈕並點擊
                        next_button = page.locator("a:has-text('下一頁'), a:has-text('>')").first
                        
                        if next_button.is_visible():
                            print("   鼠标點擊下一頁按鈕...")
                            next_button.click()
                            time.sleep(2.5)  # 點擊後等待 AJAX 渲染完成
                        else:
                            print("   🚫 找不到下一頁按鈕，提早結束翻頁。")
                            break
                    except Exception as e:
                        print(f"   ⚠️ 翻頁結束或發生異常。")
                        break

        except Exception as e:
            print(f"[錯誤] Playwright 抓取發生異常: {e}")
        finally:
            browser.close()
            
    print(f"✅ 共抓取到 {len(links_data)} 筆有效連結！")
    return source_name, links_data

# ========================================================
# 3. 【被漏掉的函數】抓取內頁完整內文 (供 main.py 第 98 行呼叫)
# ========================================================
def fetch_detail_content(url):
    """進去公告內頁，把所有的純文字抓出來，去除 HTML 標籤"""
    session = get_robust_session()
    try:
        response = session.get(url, timeout=10)
        response.encoding = response.apparent_encoding
        
        if response.status_code != 200:
            return "無法載入網頁內容"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除沒用的標籤
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
            
        # 取得純文字
        text = soup.get_text(separator="\n", strip=True)
        # 限制長度，避免單一網頁塞太多廢話撐爆 AI 的 Token 數量
        return text[:3000]
    except Exception as e:
        return f"擷取內文發生錯誤: {str(e)}"

# ========================================================
# 4. 送交 Gemini AI 進行批次清理
# ========================================================
def process_ai_batch(batch_data, prompt_template, ai_client):
    """將資料轉成文字並送交 Gemini AI 處理"""
    try:
        # 將包裝好的資料轉為純文字傳給 AI
        clean_batch = []
        for item in batch_data:
            clean_batch.append({
                "uuid": item["uuid"],
                "school_name": item["school_name"],
                "title": item["title"],
                "link": item["link"],
                "list_context": item["list_context"],
                "content": item["content"]
            })
            
        formatted_input = json.dumps(clean_batch, ensure_ascii=False, indent=2)
        full_prompt = prompt_template.replace("{batch_input}", formatted_input)
        
        # 呼叫新版 Google GenAI SDK (Gemini 2.5)
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt,
            config={
                'response_mime_type': 'application/json'
            }
        )
        
        # 解析 AI 回傳的 JSON 陣列
        result_json = json.loads(response.text)
        return result_json
    except Exception as e:
        print(f"[AI 錯誤] 批次處理失敗: {e}")
        return []
