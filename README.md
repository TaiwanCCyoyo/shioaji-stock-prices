# Shioaji Stock Prices 📈

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/platform-windows%20%7C%20linux-lightgrey)

一個基於 [Shioaji API](https://github.com/Sinotrade/Shioaji) 的台股資料自動化下載與轉檔系統。
專注於穩定、自動化的日資料更新 (Daily Update Pipeline)。

## ✨ 功能特色

- **自動化下載**：每日自動下載指定股票清單的分K資料 (`min.csv`)。
- **智慧增量更新**：自動偵測本地已有資料，只下載缺少的日期區間，節省時間與流量。
- **自動轉檔**：下載完成後自動轉換為日K資料 (`day.csv`)。
- **流量控制**：內建 Shioaji API 流量監控，超過上限自動暫停。
- **強健日誌系統**：整合 `Rich` 顯示與完整日誌記錄，支援多進程安全寫入。

## 📂 專案結構

```
shioaji_stock_prices/
├── config/              # 設定檔目錄
│   └── stock_category.json5 # 下載標的清單
├── data/                # 資料儲存目錄 (自動忽略)
├── shp_utils/           # 通用工具庫
│   └── user_logger/     # 日誌模組 (Submodule)
├── download_stock.py    # [核心] 股票下載邏輯
├── convert_stock_price.py # [核心] 分K轉日K邏輯
├── run_daily.py         # [入口] 每日排程主程式
└── .env                 # 環境變數 (API Key)
```

## 🚀 快速開始

### 1. 安裝依賴

```bash
# 使用 uv (推薦)
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 設定環境變數

請複製 `.env.example` 為 `.env` 並填入您的 Shioaji API 資訊：

```ini
API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here
```

### 3. 下載清單過濾

`data/stock_category.json5` 定義了股票類別代碼對照表。
程式會讀取此檔案，自動過濾掉被標記為 **"期權"** 的類別，只下載股票。

### 4. 執行每日更新

```bash
python run_daily.py
```

## 🛠 自動化排程 (Windows)

建議使用 Windows Task Scheduler 設定每日下午 (如 15:00) 自動執行 `run_daily.py`。

## 🛡️ 資料安全與備份 (Data Safety)

本專案採用 **高效能附加寫入 (Append Mode)** 架構，為了確保長期資料安全，建議您定期備份原始資料。

我們提供了一個備份工具：

```bash
python backup_data.py
```

這將會把 `data/` 目錄下的所有資料壓縮備份到 `backups/` 資料夾中（檔名包含時間戳記）。
建議每週執行一次此腳本。

## 📝 License

本專案採用 Apache License 2.0。