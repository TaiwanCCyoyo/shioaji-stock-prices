import download_stock
import convert_stock_price
import datetime
from shp_utils.user_logger.user_logger import get_logger


def main() -> None:
    logger = get_logger("shioaji.log")

    logger.info(f"=== 日常更新作業開始 {datetime.datetime.now()} ===")

    logger.info("\n--- 步驟 1: 下載股票資料 ---")
    try:
        download_stock.main(logger)
    except Exception as e:
        logger.info(f"下載過程中發生錯誤: {e}")
        # 即使下載失敗（部分失敗），也可以嘗試轉檔？
        # 視需求而定，這裡假設繼續執行

    logger.info("\n--- 步驟 2: 轉換資料 (分K -> 日K) ---")
    try:
        convert_stock_price.process_all(logger)
    except Exception as e:
        logger.info(f"轉檔過程中發生錯誤: {e}")

    logger.info(f"\n=== 作業結束 {datetime.datetime.now()} ===")


if __name__ == "__main__":
    main()
