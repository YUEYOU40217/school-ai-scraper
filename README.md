我幫你把設定指南調整好了！主要修正了**金鑰設定**（根據你的架構，補上了 Discord 推播需要的 Webhook）以及**爬蟲目標設定方式**（系統是讀取 `spiders/` 資料夾裡的 Python 腳本，而不是讀取 `configs/` 裡的 JSON 檔）。

我完全保留了你原本活潑簡單的風格，沒有把底層複雜的邏輯寫出來，請參考以下修改後的版本：

---

# 學校公告自動化小幫手 (School AI Scraper) (✧∇✧)

這是一個全自動的小機器人！它會定時去學校官網幫你把最新公告抓下來，並用 AI 整理得乾乾淨淨。弄好之後，你就有一個隨時更新的專屬資料庫，可以直接自動推播到你的 Discord 頻道或串接到網頁囉！ (≧▽≦)

---

## 設定指南(⌐■_■)✨

跟著以下四個步驟點一點，系統就會開始自動幫你工作啦 (ง •_•)ง：

### 1. 打開機器人寫入權限

* **去哪裡找**：專案上方的 `Settings` -> 左邊選單找 `Actions` -> `General`
* **做什麼事**：滑到最下面的 Workflow permissions，選中 **`Read and write permissions`**，然後按下 Save。

### 2. 貼上你的專屬金鑰

* **去哪裡找**：`Settings` -> `Secrets and variables` -> `Actions`
* **做什麼事**：點擊綠色的 **`New repository secret`** 按鈕，新增以下必要的鑰匙：
* `GEMINI_API_KEY`：填入你的 Google Gemini API 密碼。
* `SCRAPER_API_KEY`：填入你的 Scraper API 密碼。
* **推播金鑰（依需求新增）**：為了讓系統能把熱騰騰的公告送到 Discord，請依照你的學校名稱新增 Webhook 網址，例如 `WEBHOOK_CSU`、`WEBHOOK_NKUST`，以及提醒用的 `WEBHOOK_ALERT_CSU` 等等。



### 3. 啟動資料發佈網址

* **去哪裡找**：`Settings` -> 左邊選單找 `Pages`
* **做什麼事**：
* Source 選單拉開，選 **`Deploy from a branch`**。
* Branch 下方選 **`gh-pages`** 分支，旁邊保持 `/ (root)`，然後按下 Save。
* (設定完稍微等個一兩分鐘，你的專屬 JSONL 資料網址就會正式上線囉！╰( º∀º )╯)



### 4. 設定你要抓哪一個公告頁面

* **去哪裡找**：直接去專案裡的 `spiders/` 資料夾。
* **做什麼事**：為你想抓取的學校建立一個「專屬資料夾」（例如 `spiders/高雄科技大學/`），並在裡面放入對應的爬蟲 Python 腳本（`.py` 檔）。系統啟動時，就會自動掃描各個學校的資料夾，幫你把最新的網頁帶回來交給 AI 處理喔！
