"""
Backup Data Module

負責將 data/ 目錄下的所有股票資料壓縮備份。
建議定期執行 (例如每週一次) 以確保資料安全。
備份檔案將存放在 backups/ 目錄中。
"""

import os
import zipfile
import datetime

from config import config
from shp_utils.user_logger import get_user_logger

# 設定備份來源與目標
DATA_DIR = config.DATA_DIR
BACKUP_DIR = config.BACKUP_DIR

logger = get_user_logger("backup_data")


def backup_data():
    if not os.path.exists(DATA_DIR):
        logger.error(f"錯誤: 資料目錄 '{DATA_DIR}' 不存在，無法備份。")
        return

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        logger.info(f"已建立備份目錄: {BACKUP_DIR}")

    # 產生備份檔名 (e.g., data_backup_20240101_120000.zip)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"data_backup_{timestamp}.zip"
    zip_filepath = os.path.join(BACKUP_DIR, zip_filename)

    logger.info(f"正在備份 '{DATA_DIR}' 到 '{zip_filepath}' ...")

    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(DATA_DIR):
                for file in files:
                    # 避免備份到其中的暫存檔或非 csv 檔案?
                    # 目前全備份比較安全，包含 json5 設定檔
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=".")  # 保持 data/xxx 結構
                    zipf.write(file_path, arcname)

        logger.info(f"備份成功！檔案大小: {os.path.getsize(zip_filepath) / (1024*1024):.2f} MB")

    except Exception as e:
        logger.error(f"備份失敗: {e}")
        # 如果失敗，嘗試刪除不完整的 zip
        if os.path.exists(zip_filepath):
            os.remove(zip_filepath)


if __name__ == "__main__":
    backup_data()
