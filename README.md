# 正修科大行政公告自動化摘要 (School AI Scraper)

> **「正修的公告通知方式真的爛透了，受不了了根本是要我 24 小時盯著手機看通知！！！真不知道在想甚麼。。。。。如果也有需求就拿去用吧 ^ω^」**

一個完全由配置驅動的智慧型兩層式爬蟲系統。透過 GitHub Actions 每小時自動巡邏正修官網，利用 Gemini 深入公告內頁摘要，並自動更JSON資料。

---

## 技術規格

- **基礎模型**：Google Gemini 1.5 Flash-Lite (由 Google AI Studio 提供)
- **選用優勢**：專為高頻率、低延遲的自動化任務設計。具備超大上下文視窗（Context Window），即使公告內頁包含數千字活動規章也能輕鬆吞下，且在免費額度內運作綽綽有餘。
- **輸出格式**：採用結構化提示詞（Structured Prompting），強制 AI 扮演行政秘書，精準吐出防呆的標準 JSON 物件。

---

## 文件結構

- `scraper.py`：核心爬蟲主程式，負責兩層式網頁文字擷取與呼叫 Gemini API。
- `config.json`：控制中心。存放目標網址、爬蟲執行時段、HTML 標籤選擇器（Selector）與 AI 提示詞模板。
- `.github/workflows/run_scraper.yml`：GitHub Actions 排程設定檔，負責每小時自動喚醒機器人執行任務。

---

## 🛠️ 運行指南

### 1. 配置環境與密鑰
1. 去 [Google AI Studio](https://aistudio.google.com/) 免費申請一組 API Key。
2. 在本 GitHub 倉庫的 `Settings` -> `Secrets and variables` -> `Actions` 中，新增一個加密秘密變數。
   - **Name**: `GEMINI_API_KEY`
   - **Value**: 貼上你的 Gemini API 金鑰。

### 2. 自定義配置 (`config.json`)
可直接修改設定檔，限制爬蟲只在特定整點執行，或更換爬取標籤：
```json
{
  "urls": ["[https://www.csu.edu.tw/p/403-1000-13-1.php](https://www.csu.edu.tw/p/403-1000-13-1.php)"],
  "active_hours": [1, 7, 13, 16, 17, 19],
  "selector_config": {
    "row_selector": "tr",
    "link_selector": "a"
  }
}
