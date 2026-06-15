import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import time

# 設定假瀏覽器標頭，避免被學校網站的基礎防爬蟲機制阻擋
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def fetch_links_smart(url):
    """抓取目標網址中的所有連結與周邊文字"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding # 自動偵測編碼，避免中文亂碼
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 取得網頁標題作為來源名稱
        title_tag = soup.find('title')
        source_name = title_tag.text.strip() if title_tag else "未知網頁"
        
        links_data = []
        # 尋找所有 <a> 標籤
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            
            # 過濾掉無效或與公告無關的連結
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
                
            # 將相對路徑轉換為絕對網址
            full_url = urljoin(url, href)
            
            # 取得連結文字或 title 屬性
            link_text = a_tag.get_text(strip=True)
            if not link_text:
                link_text = a_tag.get('title', '').strip()
                
            if not link_text:
                continue

            # 抓取連結附近的文字作為「列表頁週邊文字」（幫助 AI 判斷日期或處室）
            parent = a_tag.parent
            list_context = parent.get_text(separator=' ', strip=True) if parent else ""

            links_data.append({
                "title": link_text,
                "href": full_url,
                "list_context": list_context
            })
            
        return source_name, links_data

    except Exception as e:
        print(f"[錯誤] 無法抓取連結 {url}: {e}")
        return "錯誤網頁", []

def fetch_detail_content(url):
    """進入公告內頁，把所有純文字抓下來給 AI 閱讀"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除不需要的腳本與樣式標籤，減少雜訊
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        # 取得純文字
        text = soup.get_text(separator='\n', strip=True)
        
        # 限制字數，避免單一頁面過長塞爆 AI 的 Token 限制 (抓前 3000 字通常非常夠用了)
        return text[:3000]
        
    except Exception as e:
        print(f"[警告] 無法抓取內文 {url}: {e}")
        return "無法取得內文。"

def process_ai_batch(batch, template, client):
    """將一批資料送給 Gemini 進行精準過濾與格式化"""
    try:
        # 將這批次資料轉為 JSON 字串放入提示詞
        batch_json_str = json.dumps(batch, ensure_ascii=False, indent=2)
        prompt = template.replace("{batch_input}", batch_json_str)
        
        # 呼叫 Gemini 2.5 Flash 模型 (速度快、成本低、解析能力強)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                "response_mime_type": "application/json", # 強制 AI 必定輸出合法 JSON
            }
        )
        
        # 解析 AI 傳回的 JSON 結果
        result = json.loads(response.text)
        return result
        
    except Exception as e:
        print(f"[AI 處理錯誤] 發生異常: {e}")
        # 如果發生錯誤 (如 Rate Limit)，休眠一下避免連環報錯
        time.sleep(5)
        return []
