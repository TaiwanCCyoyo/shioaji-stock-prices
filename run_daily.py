import download_stock
import convert_stock_price
import datetime
from utils.user_logger.user_logger import get_logger

# Setup Logger
logger = get_logger("shioaji.log")


def main():
    logger.info(f"=== 日常更新作業開始 {datetime.datetime.now()} ===")

    print("\n--- 步驟 1: 下載股票資料 ---")
    try:
        download_stock.main()
    except Exception as e:
        print(f"下載過程中發生錯誤: {e}")
        # 即使下載失敗（部分失敗），也可以嘗試轉檔？
        # 視需求而定，這裡假設繼續執行

    print("\n--- 步驟 2: 轉換資料 (分K -> 日K) ---")
    try:
        convert_stock_price.process_all()
    except Exception as e:
        print(f"轉檔過程中發生錯誤: {e}")

    print(f"\n=== 作業結束 {datetime.datetime.now()} ===")


if __name__ == "__main__":
    main()
