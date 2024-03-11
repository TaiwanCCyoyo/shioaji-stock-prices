# **shioaji-stock-prices**
* 使用 shioaji API 下載台股股價資訊，並存儲為 .csv 檔案
* 將下載的股價資訊轉換為日 K 資料，並存儲為 .csv 檔案

## 前置作業
* 參考 https://sinotrade.github.io/zh_TW/tutor/prepare/token/ ，取得 API Key 和 Secret Key
* 在此目錄底下新增一個 api.key，download_and_convert_stock_price.ipynb 會讀取該檔案和 shioaji API 連線
  * 第一行填 API Key
  * 第二行填 Secret Key

## 使用說明
* 詳細可以見 download_and_convert_stock_price.ipynb