# 學校公告自動化摘要 (School AI Scraper)

透過 GitHub Actions 排程定時巡邏學校官網，利用 Gemini 3.1 Flash-Lite 深入公告內頁進行智慧摘要，並自動將成果發布至 gh-pages 分支，形成一個免費且全自動更新的網頁 API (announcements.json)直接讀取。

---

## 技術規格

* 基礎模型：Google Gemini 3.1 Flash-Lite (由 Google AI Studio 提供)
---

## 系統架構與文件敘述

本系統由多個模組協同運作，核心控制主要由 scraper.py 負責，它處理歷史資料的 UUID 對照、排程檢查、年份過濾，並進行全域日期的最終降序大排序與存檔；底層的網路連線與 AI 引擎則由 utils.py 提供支援，內建底層 SSL 突破盾牌、智慧雜訊過濾器以及批次 AI JSON 生成器。整個系統的行為皆受到 config.json 控制中心的規範，裡面存放了目標學校網址，透過位於 GitHub Actions 排程設定檔，定時自動喚醒機器人執行上述完整的爬蟲與解析任務。

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
