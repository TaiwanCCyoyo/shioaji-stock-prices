"""
Convert Stock Price Module

負責將下載的分K資料 (`_min.csv`) 轉換為日K資料 (`_day.csv`)。
支援多進程 (Multiprocessing) 加速轉檔作業。
"""

import os
import logging
import pandas as pd
import re
from config import config
from concurrent.futures import ProcessPoolExecutor


from shp_utils.user_logger.user_logger import get_logger


def process_min_file(min_file: str, data_dir: str) -> str:
    pass
    """
    生成單一 _min.csv 檔案對應的日K資料。

    Args:
        min_file(str): 輸入的 _min.csv 檔案名稱。
        data_dir(str): 包含分K資料檔案的資料夾。

    Returns:
        None
    """
    day_file = re.sub(r"_min\.csv$", r"_day.csv", min_file)
    result_msg = f"將{min_file}轉成{day_file}"

    # 讀取分K資料
    min_data = pd.read_csv(os.path.join(data_dir, min_file))
    min_data.ts = pd.to_datetime(min_data.ts)
    min_data.set_index("ts", inplace=True)

    # 捨棄不合理資料 (所有數值為0的行)
    min_data = min_data[(min_data != 0).all(axis=1)]

    # [新增] OHLC 邏輯檢查
    # 檢查條件：
    # 1. High 必須大於等於 Open, Close, Low
    # 2. Low 必須小於等於 Open, Close, High
    # 3. Volume 必須大於等於 0
    invalid_mask = (
        (min_data['High'] < min_data['Open']) |
        (min_data['High'] < min_data['Close']) |
        (min_data['High'] < min_data['Low']) |
        (min_data['Low'] > min_data['Open']) |
        (min_data['Low'] > min_data['Close']) |
        (min_data['Low'] > min_data['High']) |
        (min_data['Volume'] < 0)
    )

    if invalid_mask.any():
        bad_count = invalid_mask.sum()
        # 取得錯誤資料的時間點 (前 2 筆)
        bad_rows = min_data[invalid_mask]

        details = []
        for ts in bad_rows.index[:2]:
            dt_str = ts.strftime("%Y-%m-%d %H:%M")
            try:
                # 取得原始數值 (nanoseconds) 供使用者搜尋 CSV
                ts_val = ts.value
                details.append(f"{dt_str} (TS={ts_val})")
            except Exception:
                details.append(dt_str)

        ts_str = ", ".join(details)
        if bad_count > 2:
            ts_str += "..."

        result_msg += f" [Warning] {bad_count}筆錯誤: {ts_str}"

        # 剔除異常資料，避免污染日K
        min_data = min_data[~invalid_mask]

    # 生成日K資料
    day_data = min_data.resample("1D").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    )

    day_data = day_data.dropna(subset=["Open", "High", "Low", "Close", "Volume"])

    # 計算均線
    day_data["SMA5"] = day_data["Close"].rolling(window=5).mean().round(2)
    day_data["SMA10"] = day_data["Close"].rolling(window=10).mean().round(2)
    day_data["SMA20"] = day_data["Close"].rolling(window=20).mean().round(2)
    day_data["SMA60"] = day_data["Close"].rolling(window=60).mean().round(2)
    day_data["EMA5"] = day_data["Close"].ewm(span=5).mean().round(2)
    day_data["EMA10"] = day_data["Close"].ewm(span=10).mean().round(2)
    day_data["EMA20"] = day_data["Close"].ewm(span=20).mean().round(2)
    day_data["EMA60"] = day_data["Close"].ewm(span=60).mean().round(2)

    # 將生成的日K資料存儲到 _day.csv 檔案
    day_data.to_csv(os.path.join(data_dir, day_file), index=True)
    return result_msg


def process_all(logger: logging.Logger) -> None:

    # 取得資料夾中的所有 _min.csv 檔案
    if not os.path.exists(config.DATA_DIR):
        logger.error(f"Data directory {config.DATA_DIR} does not exist.")
        return

    min_files = [f for f in os.listdir(config.DATA_DIR) if f.endswith("_min.csv")]

    if not min_files:
        logger.info("No _min.csv files found.")
        return

    logger.info(f"Found {len(min_files)} files to convert.")

    # 使用 ProcessPoolExecutor 建立 process pool
    with ProcessPoolExecutor() as executor:
        # 將任務送至 process pool 中執行
        results = executor.map(process_min_file, min_files, [config.DATA_DIR] * len(min_files))

        # 統一由主程序寫 Log，避免多程序競爭檔案寫入權限 (Windows常見問題)
        for res in results:
            if res:
                logger.info(res)


if __name__ == "__main__":
    # Setup Logger
    logger = get_logger("shioaji.log")
    process_all(logger)
