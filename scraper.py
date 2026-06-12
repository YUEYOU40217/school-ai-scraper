import json, os, sys, requests
from bs4 import BeautifulSoup
from google import genai

def run():
    config = json.loads(os.environ.get("CONFIG_JSON", "{}"))
    client = genai.Client(api_key=config.get('api_key'))
    
    final_data = []
    for url in config.get('urls', []):
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            content = soup.get_text(separator=' ', strip=True)[:2000]
            
            prompt = f"分析以下公告內容，關鍵字：{config['keywords']}。請回傳JSON陣列：[{{\"keywords\":\"...\", \"summary\":\"...\", \"link\":\"...\"}}]\n內容：{content}"
            
            res = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
            )
            data = json.loads(res.text.replace("```json", "").replace("```", "").strip())
            final_data.extend(data)
        except Exception as e:
            print(f"Error at {url}: {e}")

    with open("announcements.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run()
