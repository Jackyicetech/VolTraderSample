# 載入 tcoreapi
import time

from tcoreapi_mq import *
# 載入我們提供的行情 function
from quote_functions import *
import threading

g_QuoteZMQ = None
g_QuoteSession = ""


def main():
    global g_QuoteZMQ
    global g_QuoteSession

    # 建立 ZMQ 連線

    # 設定連線授權碼，通常不用改。
    g_QuoteZMQ = QuoteAPI("ZMQ", "8076c9867a372d2a9a814ae710c256e2")

    # 設定連接 Port，通常不用改。
    q_data = g_QuoteZMQ.Connect("51647")

    print(q_data)

    if q_data["Success"] != "OK":
        print("[ quote ]connection failed")
        return

    # 連線成功后，將取得的 Session Key 儲存下來，後面調用指令需要帶入。
    g_QuoteSession = q_data["SessionKey"]

    #############行情#############
    # 建立一個行情執行緒
    t1 = threading.Thread(target=quote_sub_th, args=(g_QuoteZMQ, q_data["SubPort"],))
    t1.daemon = True
    t1.start()

    # 即時行情訂閱
    # 設定合約代碼，測試時請注意範例的合約是否已經下市。
    testSymbol = "TC.F.TWF.MXF.202208"

    # 解訂實時報價(每次訂閱合約前，先調用解訂，避免重覆訂閱)
    g_QuoteZMQ.UnsubQuote(g_QuoteSession, testSymbol)
    # 訂閱即時行情
    g_QuoteZMQ.SubQuote(g_QuoteSession, testSymbol)
    # 訂閱五秒後自動解除訂閱
    time.sleep(5)
    # 解訂實時報價
    g_QuoteZMQ.UnsubQuote(g_QuoteSession, testSymbol)

    g_QuoteZMQ.Logout(g_QuoteSession)


if __name__ == '__main__':
    main()
