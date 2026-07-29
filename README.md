---

# 學校公告自動化小幫手 (School AI Scraper) (✧∇✧)

這是一個全自動的小機器人！它會定時去學校官網幫你把最新公告抓下來，並用 AI 整理得乾乾淨淨。弄好之後，你就有一個隨時更新的專屬資料庫，可以直接串接給你的 LINE 機器人或網頁囉！ (≧▽≦)

---

## 設定指南(⌐■_■)✨

跟著以下四個步驟點一點，系統就會開始自動幫你工作啦 (ง •_•)ง：

### 1. 打開機器人寫入權限

* **去哪裡找**：專案上方的 `Settings` -> 左邊選單找 `Actions` -> `General`
* **做什麼事**：滑到最下面的 Workflow permissions，選中 **`Read and write permissions`**，然後按下 Save。

### 2. 貼上你的專屬金鑰

* **去哪裡找**：`Settings` -> `Secrets and variables` -> `Actions`
* **做什麼事**：點擊綠色的 **`New repository secret`** 按鈕，分別新增這兩把鑰匙：
* `GEMINI_API_KEY`：填入你的 Google Gemini API 密碼。
* `SCRAPER_API_KEY`：填入你的 Scraper API 密碼。



### 3. 啟動資料發佈網址

* **去哪裡找**：`Settings` -> 左邊選單找 `Pages`
* **做什麼事**：
* Source 選單拉開，選 **`Deploy from a branch`**。
* Branch 下方選 **`gh-pages`** 分支，旁邊保持 `/ (root)`，然後按下 Save。
* (設定完稍微等個一兩分鐘，你的專屬 JSONL 資料網址就會正式上線囉！╰( º∀º )╯)



### 4. 設定你要抓哪一個公告頁面

* **去哪裡找**：直接去專案裡的 `configs/` 資料夾，打開或新增設定檔（例如 `web1.json`）。
* **做什麼事**：照著多工任務格式填入「學校名稱」，並在 `tasks` 陣列裡設定你要抓的處室公告，例如這樣：

```json
{
    "site_name": "高科大最新消息",
    "method": "GET",
    "delay": 1.5,
    "tasks": [
        {
            "category": "最新消息",
            "url_pattern": "[https://www.nkust.edu.tw/p/422-1000-1001-](https://www.nkust.edu.tw/p/422-1000-1001-){page}.php?Lang=zh-tw",
            "start_page": 1,
            "end_page": 5
        }
    ]
}
