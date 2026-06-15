import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils import fetch_html_text

def parse_html_to_links(html_text, target_url):
    """強制解析 HTML，不忽略任何找到的標籤"""
    if not html_text: return "未命名網頁", []
    
    soup = BeautifulSoup(html_text, "html.parser")
    links = []
    all_a_tags = soup.find_all('a')
    
    for a_tag in all_a_tags:
        title = a_tag.get_text(strip=True)
        href = a_tag.get('href')
        
        # 排除無意義連結
        if not href or len(title) < 5: continue
        if any(w in title.lower() for w in ["跳到", "首頁", "menu", "交通", "login"]): continue
            
        full_url = urljoin(target_url, href)
        
        # 強制尋找日期：往上找 10 層，若都沒找到日期則標記 UNRESOLVED
        date_str = "UNRESOLVED"
        parent = a_tag
        for _ in range(10):
            parent = parent.parent
            if not parent: break
            row_text = parent.get_text(separator=' ', strip=True)
            # 匹配 YYYY/MM/DD 或 YYYY-MM-DD
            date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', row_text)
            if date_match:
                date_str = date_match.group(1)
                break
        
        links.append({
            "title": title,
            "href": full_url,
            "date": date_str
        })
    return soup.title.get_text(strip=True), links

def main():
    target_url = "https://www.csu.edu.tw/p/403-1000-13-1.php?Lang=zh-tw"
    print(f"開始抓取: {target_url}")
    
    html = fetch_html_text(target_url)
    name, links = parse_html_to_links(html, target_url)
    
    # 將所有結果寫入檔案，方便你除錯
    output_data = {name: links}
    with open("raw_scraped_data.json", 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print(f"處理完成！已抓取 {len(links)} 筆連結至 raw_scraped_data.json")

if __name__ == "__main__":
    main()
