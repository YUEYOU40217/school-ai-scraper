# 學校公告自動化摘要 (School AI Scraper)

透過 GitHub Actions 每小時自動巡邏正修官網，利用 Gemini 深入公告內頁摘要，並自動更新 JSON 資料。

---

## 技術規格

- **基礎模型**：Google Gemini 3.1 Flash-Lite (由 Google AI Studio 提供)
- **選用優勢**：專為高頻率、低延遲的自動化任務設計。系統內建「10 筆批次打包 (Batching)」黑科技，將多則標題打包一次送給 AI，大幅降低 90% 的 API 呼叫頻率，完美避開免費額度的每分鐘限制（429 錯誤），在免費額度內運作綽綽有餘。
- **核心技術**：
  - **智慧無格式盲猜**：拋棄傳統易碎的 HTML 選擇器（Selector），程式會自動在網頁中盲猜、定位公告與日期，學校改版也不會死機。
  - **底層 SSL 強行突破**：內建 urllib 雙重保險連線機制，完全繞過系統底層的憑證連線限制，保證學校網站不漏抓。
  - **全域最新日期排序**：自動校正民國年與西元格式，所有抓到的公告不分學校，一律按照最新時間由上至下（降序）大洗牌並重新編號。
- **輸出格式**：採用結構化提示詞（Structured Prompting）輸出精準對齊之 JSON 陣列。

---

## 文件結構

- `scraper.py`：核心控制主程式。負責排程檢查、年份過濾、將合法資料切片打包，並進行最終的全域日期大排序與存檔。
- `utils.py`：網路連線與 AI 引擎。內建底層 SSL 突破盾牌、智慧導覽雜訊過濾器，以及批次 AI JSON 生成器。
- `config.json`：控制中心。存放多個目標學校網址、允許抓取的年份、執行時段與批次處理的 Prompt 提示詞模板。
- `.github/workflows/run_scraper.yml`：GitHub Actions 排程設定檔，負責每小時自動喚醒機器人執行任務。

---

## 運行指南

### 1. 配置環境與密鑰
1. 去 [Google AI Studio](https://aistudio.google.com/) 免費申請一組 API Key。
2. 在本 GitHub 倉庫的 `Settings` -> `Secrets and variables` -> `Actions` 中，新增一個加密秘密變數。
   - **Name**: `GEMINI_API_KEY`
   - **Value**: 貼上你的 Gemini API 金鑰。

### 2. 自定義配置 (`config.json`)
擺脫複雜標籤！現在你只需要提供學校名稱、網址、想抓的年份與整點時段即可：
```json
{
  "allowed_years": [2025, 2026],
  "scheduled_hours": [0, 12],
  "sites": [
    {
      "name": "正修科技大學",
      "url": "[https://www.csu.edu.tw/p/403-1000-13-1.php](https://www.csu.edu.tw/p/403-1000-13-1.php)"
    }
  ],
  "prompt_template": "請分析以下多則學校公告標題，並依序為每一則標題萃取出 1 到 5 個繁體中文關鍵字...{batch_input}"
}
