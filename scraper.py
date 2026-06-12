import json, requests
from bs4 import BeautifulSoup
from google import genai

def run():
    # 直接讀取同目錄下的 config.json
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    client = genai.Client(api_key=config['api_key'])
    final_data = []

    for url in config.get('urls', []):
        try:
            resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.text, "html.parser")
            content = soup.get_text(separator=' ', strip=True)[:2500]
            
            prompt = f"{config['prompt']}\n關鍵字：{config['keywords']}\n網頁內容：{content}\n請回傳嚴格的 JSON 陣列格式：[{{\"keywords\":\"...\", \"summary\":\"...\", \"link\":\"...\"}}]"
            
            res = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
            )
            data = json.loads(res.text.replace("```json", "").replace("```", "").strip())
            final_data.extend(data)
        except Exception as e:
            print(f"Error: {e}")

    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run()
    
