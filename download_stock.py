"""
Download Stock Module

負責從 Shioaji API 下載股票分K資料 (1分K)。
具備斷點續傳、流量控制與錯誤重試機制。
"""

import shioaji as sj
import pandas as pd
import os
import datetime
import re
import json5
import logging
from config import config
from dotenv import load_dotenv


# Re-export or just use local typing

def get_last_timestamp_from_csv(file_path: str, date_col_name: str = 'ts') -> datetime.datetime:
    """
    Efficiently read the last timestamp from a CSV file without loading the whole file.
    Reads the header to find `date_col_name` index, then reads the last line.
    """
    try:
        with open(file_path, 'rb') as f:
            # 1. Read Header
            header_line = f.readline().decode('utf-8').strip()
            if not header_line:
                return None

            headers = header_line.split(',')
            try:
                date_col_index = headers.index(date_col_name)
            except ValueError:
                return None

            # 2. Seek to End
            try:
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b'\n':
                    f.seek(-2, os.SEEK_CUR)
            except OSError:
                # File is too small (e.g. only header or empty)
                return None

            last_line = f.readline().decode('utf-8')
            if not last_line:
                return None

            # Avoid parsing header as data if file has only 1 line
            if last_line.strip() == header_line:
                return None

            # 3. Parse Last Line
            parts = last_line.strip().split(',')
            ts_str = parts[date_col_index]

            # Handle numeric timestamps
            try:
                # Try converting to float first, then int
                ts_val = int(float(ts_str))
                return pd.to_datetime(ts_val)
            except ValueError:
                # Not a number, try parsing as string
                return pd.to_datetime(ts_str)

    except (IOError, IndexError, ValueError):
        return None


def get_contract_list(api: sj.Shioaji, stock_category: dict) -> list:
    """取得代下載的股票列表"""
    TSE_contract_list = api.Contracts.Stocks.TSE
    OTC_contract_list = api.Contracts.Stocks.OTC

    contract_list = []

    # 上市股票
    # 排除期權
    if "TSE" in stock_category:
        option_code = [key for key, value in stock_category["TSE"].items() if value == "期權"]
    else:
        option_code = []

    for contract in TSE_contract_list:
        if contract.category not in option_code and re.match("^[0-9]+$", contract.code):
            contract_list.append(contract)

    # 上櫃股票
    if "OTC" in stock_category:
        option_code = [key for key, value in stock_category["OTC"].items() if value == "期權"]
    else:
        option_code = []

    for contract in OTC_contract_list:
        if contract.category not in option_code and re.match("^[0-9]+$", contract.code):
            contract_list.append(contract)

    # 大盤指數
    if "001" in api.Contracts.Indexs.TSE:
        contract_list.append(api.Contracts.Indexs.TSE["001"])

    # 排序
    contract_list = sorted(contract_list, key=lambda x: x.code)
    return contract_list


def update_stock_symbol_mapping(api: sj.Shioaji, logger: logging.Logger) -> None:
    """更新並儲存股號股名對照表"""
    all_contracts = []
    all_contracts.extend(api.Contracts.Stocks.TSE)
    all_contracts.extend(api.Contracts.Stocks.OTC)
    if "001" in api.Contracts.Indexs.TSE:
        all_contracts.append(api.Contracts.Indexs.TSE["001"])

    stock_symbol_mapping = {item.code: item.name for item in all_contracts}
    stock_symbol_mapping = dict(sorted(stock_symbol_mapping.items()))

    with open(config.STOCK_SYMBOL_MAPPING, "w", encoding="utf-8") as f:
        json5.dump(stock_symbol_mapping, f, ensure_ascii=False, indent=4)
    logger.info(f"對照表已經儲存至 {config.STOCK_SYMBOL_MAPPING}")


def main(logger: logging.Logger) -> None:

    load_dotenv()

    # 檢查 API key 是否存在
    if "API_KEY" not in os.environ or "SECRET_KEY" not in os.environ:
        logger.error("Error: API_KEY or SECRET_KEY not found in environment variables.")
        return

    api = sj.Shioaji()

    # Login
    logger.info("登入 Shioaji API...")
    api.login(api_key=os.environ["API_KEY"], secret_key=os.environ["SECRET_KEY"])

    try:
        # 載入 Stock Category
        logger.info(f"Loading stock category from {config.STOCK_CATEGORY}")
        if os.path.exists(config.STOCK_CATEGORY):
            with open(config.STOCK_CATEGORY, "r", encoding="utf-8") as f:
                stock_category = json5.load(f)
        else:
            logger.warning("Warning: Stock category file not found. Assuming empty.")
            stock_category = {"TSE": {}, "OTC": {}}

        # 更新 Symbol Mapping
        update_stock_symbol_mapping(api, logger)

        # 取得下載清單
        contract_list = get_contract_list(api, stock_category)
        logger.info(f"共取得 {len(contract_list)} 檔標的")

        start_time = datetime.datetime.now()
        today_date = start_time
        today_str = today_date.strftime("%Y-%m-%d")
        downloadable = True

        # 建立 data 目錄
        if not os.path.exists(config.DATA_DIR):
            os.makedirs(config.DATA_DIR)

        for contract in contract_list:
            stock_file = f"{config.DATA_DIR}/{contract.code}_min.csv"

            start_date_str = config.SHIOAJI_START_DATE
            # Parse default start date to datetime object for comparison
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")

            if os.path.isfile(stock_file):
                logger.debug(f"讀取{contract.name} ({contract.code}) 的最後一筆資料時間")
                try:
                    # Optimization: Read only the last line to get timestamp
                    last_ts = get_last_timestamp_from_csv(stock_file, date_col_name='ts')

                    if last_ts:
                        # 從最後一筆資料的隔天開始抓
                        start_date_str = (last_ts + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        start_date = datetime.datetime.strptime(f"{start_date_str} 08:00", "%Y-%m-%d %H:%M")
                    else:
                        # File might be empty or header only
                        pass

                except Exception as e:
                    logger.warning(f"警告: {stock_file} 讀取失敗，可能是檔案損毀 ({e})")
                    logger.info("將重新下載此檔完整資料...")

                    # 把壞掉的檔案改名備份 (例如 xx.csv.bak)，避免影響後續流程
                    try:
                        os.rename(stock_file, stock_file + ".bak")
                        logger.info(f"已將損毀檔案備份為: {stock_file}.bak")
                    except OSError:
                        pass

                    # 重置 start_date 為預設值，確保重新下載完整區間
                    start_date_str = config.SHIOAJI_START_DATE
                    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")

            # 若 start_date 已經大於等於今天，代表無需更新
            if start_date >= today_date:
                logger.debug(f"跳過{contract.name} ({contract.code}) 因為已經擁有 {start_date_str} 之前的資料")
                continue

            success = False
            df_new = pd.DataFrame()
            logger.info(f"嘗試取得{contract.name} ({contract.code}) 從 {start_date_str} 到 {today_str} 的資料")

            stock_get_start = datetime.datetime.now()
            try:
                kbars = api.kbars(contract=contract, start=start_date_str, end=today_str)
                df_new = pd.DataFrame({**kbars})
            except Exception as e:
                logger.error(f"取得失敗: {e}")
                df_new = pd.DataFrame()  # Ensure empty df

            stock_get_end = datetime.datetime.now()
            logger.debug(f"共花費: {(stock_get_end - stock_get_start).total_seconds()} 秒")

            # 檢查流量
            if df_new.empty:
                try:
                    usage_bytes = api.usage().bytes
                    if usage_bytes >= 524288000:  # 500MB limit
                        logger.warning(f"今日已使用 {usage_bytes} B (達上限)")
                        downloadable = False
                except Exception:
                    pass
            else:
                success = True

            if not downloadable:
                logger.warning("流量已達上限，停止下載。")
                break

            if not success:
                logger.warning(f"跳過{contract.name} ({contract.code}) 因為從 {start_date_str} 到 {today_str} 的資料取得失敗")
                continue

            # 存檔與合併邏輯
            try:
                # 判斷是附加模式 (Append) 還是 覆蓋模式 (Overwrite)
                # 如果檔案存在且不是重新完整下載 (start_date 非預設值)，則使用附加模式
                is_append = False
                if os.path.isfile(stock_file) and start_date_str != config.SHIOAJI_START_DATE:
                    is_append = True

                if is_append:
                    logger.debug(f"將新資料附加到 {contract.name} ({contract.code})")
                    # 安全檢查：讀取舊檔 Header 確保欄位順序一致
                    try:
                        existing_columns = pd.read_csv(stock_file, nrows=0).columns.tolist()
                        # 重排 df_new 欄位以符合舊檔
                        df_new = df_new[existing_columns]

                        # 附加模式: header=False
                        df_new.to_csv(stock_file, mode='a', header=False, index=False)

                    except Exception as e:
                        logger.error(f"{stock_file} 附加失敗: {e}")
                        logger.error("建議檢查該檔案欄位是否變更，或刪除後重抓。")
                        continue
                else:
                    # 全新檔案或完整重新下載
                    logger.info("建立/覆蓋本地股票資料檔")
                    df_new.to_csv(stock_file, mode='w', header=True, index=False)

            except Exception as e:
                logger.error(f"{stock_file} 儲存失敗: {e}")
                if not is_append:
                    # 只有在覆蓋模式失敗時才考慮刪除殘檔，附加失敗不應刪除原檔
                    try:
                        os.remove(stock_file)
                    except OSError:
                        pass

        end_time = datetime.datetime.now()
        logger.info(f"結束: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"程式共花費: {(end_time - start_time).total_seconds()} 秒")

    except Exception as e:
        logger.error(f"發生未預期錯誤: {e}")
    finally:
        api.logout()


if __name__ == "__main__":
    from shp_utils.user_logger.user_logger import get_logger
    logger = get_logger("shioaji.log")
    main(logger)
