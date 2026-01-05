# config.py

# 在整個專案中，這個目錄的名稱應該保持一致，以確保各個部分都能正確引用相同的目錄。

# DATA_DIR 是用於定義預設的資料緩存目錄。
DATA_DIR = "data"

# STOCK_CATEGORY 用於定義預設的股票類型對照表
STOCK_CATEGORY = 'data/stock_category.json5'

# STOCK_SYMBOL_MAPPING  用於定義預設的股票股號對照表
STOCK_SYMBOL_MAPPING = 'data/stock_symbol_mapping.json5'

# SHIOAJI_START_DATE 用於定義 shioaji 資料的起始日期
SHIOAJI_START_DATE = '2018-12-07'

# API_KEY 用於定義預設的 api 放置的檔案
# 第一行寫 API key
# 第二行寫 Secret key
API_KEY = 'api.key'

# BACKUP_DIR 用於定義預設的備份目錄
BACKUP_DIR = "backups"
