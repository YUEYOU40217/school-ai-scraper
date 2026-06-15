# 記得在檔案最上方加入這行 import
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

def fetch_links_smart(url, max_pages=3):
    """使用 Playwright 真實瀏覽器抓取目標網頁，並自動翻頁"""
    print(f"🔍 啟動 Playwright 瀏覽器準備抓取: {url}")
    
    links_data = []
    source_name = "未知網頁"
    
    # 啟動 Playwright
    with sync_playwright() as p:
        # ⚠️ 在 GitHub 上必須設為 headless=True (無頭模式背景執行)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url)
            # 等待網頁初始載入完成
            page.wait_for_load_state('networkidle')
            
            source_name = page.title()
            
            ignore_keywords = ["首頁", "english", "在校生", "家長", "校友", "行事曆", "聯絡我們"]

            # 自動翻頁迴圈
            for current_page in range(1, max_pages + 1):
                print(f"   📄 正在解析第 {current_page} 頁...")
                
                # 取得當前網頁渲染後的完整 HTML
                html_content = page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 解析連結 (這部分保留我們之前寫好的智慧避障邏輯)
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
                        # 尋找包含「下一頁」或「>」的按鈕並點擊 (需依據學校網站按鈕名稱調整)
                        # 正修科大的分頁按鈕通常可以用 text="下一頁" 或 css selector 找到
                        next_button = page.locator("a:has-text('下一頁'), a:has-text('>')").first
                        
                        if next_button.is_visible():
                            print("   🖱️ 找到下一頁按鈕，點擊翻頁中...")
                            next_button.click()
                            # 點擊後等待新資料載入 (等待 2 秒確保 AJAX 渲染完成)
                            time.sleep(2)
                        else:
                            print("   🚫 找不到下一頁按鈕，提早結束翻頁。")
                            break
                    except Exception as e:
                        print(f"   ⚠️ 翻頁失敗或已達最後一頁。({e})")
                        break

        except Exception as e:
            print(f"[錯誤] Playwright 抓取發生異常: {e}")
            
        finally:
            browser.close()
            
    print(f"✅ 共抓取到 {len(links_data)} 筆有效連結！")
    return source_name, links_data
