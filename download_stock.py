# -*- coding: utf-8 -*-
import shioaji as sj
import pandas as pd
import os
import datetime
import re
import json5
from config import config
from dotenv import load_dotenv


def get_contract_list(api, stock_category):
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


def update_stock_symbol_mapping(api):
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
    print(f"對照表已經儲存至 {config.STOCK_SYMBOL_MAPPING}")


def main():
    load_dotenv()

    # 檢查 API key 是否存在
    if "API_KEY" not in os.environ or "SECRET_KEY" not in os.environ:
        print("Error: API_KEY or SECRET_KEY not found in environment variables.")
        return

    api = sj.Shioaji()

    # Login
    print("登入 Shioaji API...")
    api.login(api_key=os.environ["API_KEY"], secret_key=os.environ["SECRET_KEY"])

    try:
        # 載入 Stock Category
        print(f"Loading stock category from {config.STOCK_CATEGORY}")
        if os.path.exists(config.STOCK_CATEGORY):
            with open(config.STOCK_CATEGORY, "r", encoding="utf-8") as f:
                stock_category = json5.load(f)
        else:
            print("Warning: Stock category file not found. Assuming empty.")
            stock_category = {"TSE": {}, "OTC": {}}

        # 更新 Symbol Mapping
        update_stock_symbol_mapping(api)

        # 取得下載清單
        contract_list = get_contract_list(api, stock_category)
        print(f"共取得 {len(contract_list)} 檔標的")

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
                print(f"讀取{contract.name} ({contract.code}) 的資料")
                try:
                    df = pd.read_csv(stock_file)
                    df.ts = pd.to_datetime(df.ts)
                    if not df.empty:
                        # 從最後一筆資料的隔天開始抓
                        last_ts = df.iloc[-1]["ts"]
                        start_date_str = (last_ts + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        start_date = datetime.datetime.strptime(f"{start_date_str} 08:00", "%Y-%m-%d %H:%M")
                except Exception as e:
                    print(f"警告: {stock_file} 讀取失敗，可能是檔案損毀 ({e})")
                    print("將重新下載此檔完整資料...")

                    # 把壞掉的檔案改名備份 (例如 xx.csv.bak)，避免影響後續流程
                    try:
                        os.rename(stock_file, stock_file + ".bak")
                        print(f"已將損毀檔案備份為: {stock_file}.bak")
                    except OSError:
                        pass

                    # 重置 start_date 為預設值，確保重新下載完整區間
                    start_date_str = config.SHIOAJI_START_DATE
                    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")

            # 若 start_date 已經大於等於今天，代表無需更新
            # Note: start_date 包含時間若為 08:00，today_date 為當下時間。
            # 比較時若 start_date day >= today day?
            # 原邏輯: if start_date >= today_date:
            if start_date >= today_date:
                print(f"跳過{contract.name} ({contract.code}) 因為已經擁有 {start_date_str} 之前的資料")
                continue

            success = False
            df_new = pd.DataFrame()
            print(f"嘗試取得{contract.name} ({contract.code}) 從 {start_date_str} 到 {today_str} 的資料")

            stock_get_start = datetime.datetime.now()
            try:
                kbars = api.kbars(contract=contract, start=start_date_str, end=today_str)
                df_new = pd.DataFrame({**kbars})
            except Exception as e:
                print(f"取得失敗: {e}")
                df_new = pd.DataFrame()  # Ensure empty df

            stock_get_end = datetime.datetime.now()
            print(f"共花費: {(stock_get_end - stock_get_start).total_seconds()} 秒")

            # 檢查流量
            if df_new.empty:
                try:
                    usage_bytes = api.usage().bytes
                    if usage_bytes >= 524288000:  # 500MB limit
                        print(f"今日已使用 {usage_bytes} B (達上限)")
                        downloadable = False
                except Exception:
                    pass
            else:
                success = True

            if not downloadable:
                print("流量已達上限，停止下載。")
                break

            if not success:
                print(f"跳過{contract.name} ({contract.code}) 因為從 {start_date_str} 到 {today_str} 的資料取得失敗")
                continue

            # 合併並存檔
            if os.path.isfile(stock_file):
                print(f"再次讀取{contract.name} ({contract.code}) 的資料")
                try:
                    df_old = pd.read_csv(stock_file)
                    print("合併資料")
                    # concat logic
                    df_final = pd.concat([df_old, df_new], axis=0)
                except Exception as e:
                    print(f"{stock_file} 合併失敗: {e}")
                    raise e
            else:
                df_final = df_new

            try:
                print("將資料存儲到本地股票資料")
                df_final.to_csv(stock_file, index=False)
            except Exception as e:
                print(f"{stock_file} 儲存失敗: {e}")
                # 原邏輯有嘗試刪除檔案，這有點危險，暫時保留原邏輯
                try:
                    os.remove(stock_file)
                except OSError:
                    pass

        end_time = datetime.datetime.now()
        print(f"結束: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"程式共花費: {(end_time - start_time).total_seconds()} 秒")

    except Exception as e:
        print(f"發生未預期錯誤: {e}")
    finally:
        api.logout()


if __name__ == "__main__":
    main()
