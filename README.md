# 公告自動化關鍵字萃取器 (School AI Scraper)

一個基於 GitHub Actions 運作的輕量化、超高效跨校公告爬蟲系統。透過「智慧無格式盲猜」與「底層安全繞過」技術，自動巡邏各大校園官網，並利用 Gemini 將公告批次打包，精準萃取出結構化的繁體中文關鍵字，最後按發布時間進行全域排序。

---

## 核心技術與優勢

* 智慧無格式盲猜：完全拋棄傳統爬蟲易碎的 HTML 選擇器（Selector）配置。系統會自動在網頁中盲猜、定位公告結構與日期，學校網站改版也不會死機。
* 底層 SSL 雙重強行突破：針對部分學校（如高科大）頑固的 SSL 憑證驗證錯誤，直接使用 Python 最底層的 urllib 與完全不驗證的 SSL 上下文進行硬核解析，保證不漏抓。
* 10 筆批次打包 (Batching)：將抓到的公告以每 10 筆為一個包裹一次性餵給 AI。將 API 呼叫次數暴減 90%，徹底解決免費版 API 單分鐘頻率限制（429 Too Many Requests）的痛點。
* 全域最新日期排序：自動將民國年、斜線、橫線等奇形怪狀的校方日期統一編譯，不分學校，一律按照最新時間由上至下（降序）大洗牌並重新編號存檔。

---

## 技術規格

* 基礎模型：Google Gemini 3.1 Flash-Lite (由 Google AI Studio 提供)
* 模型優勢：專為高頻率、低延遲的自動化任務設計，具備超大上下文視窗，一口氣吞下 10 則公告標題進行語意分析輕而易舉，且完全在免費額度內高速運轉。
* 輸出格式：嚴格對齊之 JSON 陣列。

---

## 文件結構

* scraper.py：核心控制主程式。負責排程檢查、年份過濾、將合法資料切片打包，並進行最終的全域日期大排序與存檔。
* utils.py：網路連線與 AI 引擎。內建底層 SSL 突破盾牌、智慧導覽雜訊過濾器，以及批次 AI JSON 生成器。
* config.json：控制中心。存放多個目標學校網址、允許抓取的年份、執行時段與批次處理的 Prompt 提示詞模板。
* .github/workflows/run_scraper.yml：GitHub Actions 自動化腳本，負責定時自動喚醒機器人執行任務。

---

## 運行指南

### 1. 配置環境與密鑰
1. 前往 Google AI Studio 免費申請一組 API Key。
2. 在本 GitHub 倉庫的 Settings -> Secrets and variables -> Actions 中，新增一個加密秘密變數。
    * Name: GEMINI_API_KEY
    * Value: 貼上你的 Gemini API 金鑰。

### 2. 自定義配置 (config.json)
擺脫複雜標籤！現在你只需要提供學校名稱、網址、想抓的年份與整點時段即可：

```json
{
  "allowed_years": [2025, 2026],
  "scheduled_hours": [3, 8, 10, 16],
  "sites": [
    {
      "name": "正修科技大學",
      "url": "[https://www.csu.edu.tw/p/403-1000-13-1.php](https://www.csu.edu.tw/p/403-1000-13-1.php)"
    },
    {
      "name": "國立高雄科技大學",
      "url": "[https://www.nkust.edu.tw/p/424-1000-7-1.php?Lang=zh-tw](https://www.nkust.edu.tw/p/424-1000-7-1.php?Lang=zh-tw)"
    }
  ],
  "prompt_template": "請分析以下多則學校公告標題，並依序為每一則標題萃取出 1 到 5 個繁體中文關鍵字...{batch_input}"
}
