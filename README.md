# 學校公告自動化摘要 (School AI Scraper)

本專案透過 GitHub Actions 定時自動爬取學校官網公告，搭配 Scraper API 突破校園防火牆限制，並利用 Gemini AI 批次進行智慧摘要。最終將整理好的資料生成一個持續更新的 `announcements.json` API，方便後續直接串接個人網頁或 LINE 機器人。 (⌐■_■)

---

## 使用者自行設定指南

如果你是初次部署，請至專案的 **Settings** (設定) 完成以下四個步驟，系統就會開始全自動運作：

### 1. 開啟 Actions 寫入權限

* **路徑**：Settings -> Actions -> General
* **設定**：滑到最底部的 Workflow permissions，選取 **Read and write permissions** 並存檔。（確保機器人能自動將爬取的資料推送到專案內）

### 2. 填寫 API 金鑰 (Secrets)

* **路徑**：Settings -> Secrets and variables -> Actions
* **設定**：點擊 **New repository secret**，分別新增以下兩把金鑰：
* `GEMINI_API_KEY`：你的 Google Gemini 授權碼。
* `SCRAPER_API_KEY`：你的 Scraper API 跳板授權碼。



### 3. 啟動 GitHub Pages 網址

* **路徑**：Settings -> Pages
* **設定**：Source 選擇 **Deploy from a branch**，Branch 選擇 **gh-pages** 分支，資料夾選擇 `/ (root)` 並存檔。（設定完成後，你就會獲得一個公開且自動更新的 JSON 連結）

### 4. 自訂你要爬的學校目標

直接打開專案目錄下的 `config.json`，填入你想抓取的年份限制與學校網址即可：

```json
{
  "allowed_years": [2025, 2026],
  "sites": [
    {
      "name": "學校名稱",
      "url": "你想抓取的公告網址"
    }
  ]
}

```
