# 學校公告自動化摘要 (School AI Scraper)

透過 GitHub Actions 排程定時巡邏學校官網，利用 Gemini 3.1 Flash-Lite 深入公告內頁進行智慧摘要，並自動將成果發布至 gh-pages 分支，形成一個免費且全自動更新的網頁 API (announcements.json)，供未來 LINE 機器人或網頁直接讀取。

---

## 技術規格

* 基礎模型：Google Gemini 3.1 Flash-Lite (由 Google AI Studio 提供)
* 批次優化：內建「10 筆批次打包 (Batching)」機制，將多則標題整合為單次 AI 請求，大幅降低 90% 的 API 呼叫頻率，完美避開免費額度的每分鐘限制（429 錯誤）。
* 核心技術：
* 智慧無格式盲猜：拋棄傳統易碎的 HTML 選擇器（Selector），自動在網頁中定位公告與日期，網站改版也不會死機。
* 底層 SSL 強行突破：內建 urllib 雙重保險連線機制，完全繞過系統底層憑證連線限制。
* 全域最新日期排序：自動校正民國年與西元格式，所有公告一律按最新時間降序洗牌並重新分配、保留 UUID。



---

## 系統架構與文件敘述

本系統由多個模組協同運作，核心控制主要由 scraper.py 負責，它處理歷史資料的 UUID 對照、排程檢查、年份過濾，並進行全域日期的最終降序大排序與存檔；底層的網路連線與 AI 引擎則由 utils.py 提供支援，內建底層 SSL 突破盾牌、智慧雜訊過濾器以及批次 AI JSON 生成器。整個系統的行為皆受到 config.json 控制中心的規範，裡面存放了目標學校網址、允許抓取的年份、以及批次處理的 Prompt 提示詞模板。最後，透過位於 .github/workflows/run_scraper.yml 的 GitHub Actions 排程設定檔，定時自動喚醒機器人執行上述完整的爬蟲與解析任務。

---

## 核心部署指南 (只需完成 3 個設定)

要讓這套自動化產線完美運作，請至 GitHub 儲存庫的 Settings (齒輪) 完成以下設定：

### 1. 開啟權限 (Workflow Permissions)

* 進入 Settings -> Actions -> General
* 滑到最底部，將 Workflow permissions 改為 Read and write permissions 並存檔（確保機器人能把資料寫入 gh-pages 分支）。

### 2. 藏入金鑰 (Repository Secret)

* 進入 Settings -> Secrets and variables -> Actions
* 點擊 New repository secret：
* Name: GEMINI_API_KEY
* Value: 貼上從 Google AI Studio 免費申請的 API 金鑰。



### 3. 打开 API 網址 (GitHub Pages)

* 進入 Settings -> Pages
* 在 Build and deployment -> Source 選擇 Deploy from a branch。
* 在下方 Branch 選擇 gh-pages 分支，資料夾維持 / (root) 並存檔（開啟後即可獲得免費的 JSON API 網址）。

---

## 自定義配置 (config.json)

```json
{
  "allowed_years": [2025, 2026],
  "sites": [
    {
      "name": "正修科技大學",
      "url": "https://www.csu.edu.tw/p/403-1000-13-1.php"
    }
  ],
  "prompt_template": "請分析以下多則學校公告標題，並依序為每一則標題萃取出 1 到 5 個繁體中文關鍵字...{batch_input}"
}

```
