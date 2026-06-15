import json
import re

def fetch_links_smart(url):
    """
    這是您的智慧列表頁爬蟲函數。
    此處維持您原本的實作邏輯即可，不用因為 AI 調整而變動。
    回傳範例：return "來源名稱", [{"title": "...", "href": "...", "list_context": "..."}]
    """
    # 這裡保留您原本的 requests / BeautifulSoup 或 Playwright 程式碼
    # 以下僅為結構示意，請勿覆蓋您原本寫好的爬蟲邏輯
    return "學校公告", []


def fetch_detail_content(url):
    """
    這是您的內頁內文抓取函數。
    此處維持您原本的實作邏輯即可，不用因為 AI 調整而變動。
    回傳範例：return "內頁完整文字內文"
    """
    # 這裡保留您原本抓取內文的程式碼
    # 以下僅為結構示意，請勿覆蓋您原本寫好的爬蟲邏輯
    return "這是內頁的原始文字內容"


def process_ai_batch(batch, template, client):
    """
    配合新架構修改的 AI 批次處理函數。
    1. 完整保留並傳遞 Python 生成的 uuid。
    2. 採用新版 google-genai SDK 語法。
    3. 具備 Markdown 標籤自動防禦清理機制。
    """
    # 1. 將包含 uuid 的當前批次資料，轉換為 JSON 字串
    batch_input_str = json.dumps(batch, ensure_ascii=False)
    
    # 2. 將 JSON 字串注入到已經填入年份的提示詞範本中
    prompt = template.format(batch_input=batch_input_str)
    
    try:
        # 3. 呼叫新版 Google GenAI SDK 語法
        # 推薦使用 gemini-2.5-flash，速度極快且對 JSON 格式與指令遵循度極高
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        ai_text = response.text.strip()
        
        # 4. 防禦性機制：雖然 Prompt 強烈要求不要 Markdown 區塊，但預防 AI 偶爾不聽話
        # 如果發現開頭帶有 ```json 或 ```，用正則表達式將其徹底拔除
        if ai_text.startswith("```"):
            ai_text = re.sub(r'^
http://googleusercontent.com/immersive_entry_chip/0
