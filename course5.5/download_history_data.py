# 載入 tcoreapi
from tcoreapi_mq import *
# 載入我們提供的行情 function
from quote_functions import *
import threading
import pandas as pd

g_QuoteZMQ = None
g_QuoteSession = ""


def main():
    global g_QuoteZMQ
    global g_QuoteSession
    global testSymbol

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

    #####################################################################行情################################################
    # 建立一個行情執行緒
    t1 = threading.Thread(target=quote_sub_th, args=(g_QuoteZMQ, q_data["SubPort"],))
    t1.daemon = True
    t1.start()

    # 即時行情訂閱
    # 設定合約代碼，測試時請注意範例的合約是否已經下市。
    # testSymbol = "TC.F.TWF.TXF.202201"
    # testSymbol = "TC.O.TWF.TXO.202201.C.18400"
    # HOT:熱門月，HOT2:次熱門月，TXF:台指期貨，MXF:小台指期貨
    testSymbol = 'TC.F.TWF.TXF.HOT'

    # 訂閱歷史數據
    # message["DataType"]="TICKS"   ticks
    # message["DataType"]="1K"   1K
    # message["DataType"]="DK"   日K
    # message["DataType"]="DOGSS"   Greeks 秒數據
    # message["DataType"]="DOGSK"   Greeks 分鐘數據
    # 回補區間設定
    # yyyymmddHH, HH 00-23
    ktype = '1K'
    sD = '2022070400'
    eD = '2022070423'

    # 顯示歷史數據
    data = GetHistory(g_QuoteZMQ, g_QuoteSession, testSymbol, ktype, sD, eD)
    print(data['Time'])
    for i in range(len(data['Time'])):

        if len(str(data["Time"][i])) == 4:
            data["Time"][i] = "00" + str(data["Time"][i])[:2]
        elif len(str(data["Time"][i])) == 5:
            data["Time"][i] = "0" + str(data["Time"][i])[:3]
        elif len(str(data["Time"][i])) == 6:
            data["Time"][i] = str(data["Time"][i])[:4]



    # 確定歷史資料的類型，需要pandas裡DataFrame的格式才能使用to_csv函式轉成csv檔
    print(type(data))
    data.to_csv('history_data.csv', index=False)
    # 解除訂閱歷史數據
    g_QuoteZMQ.UnsubHistory(g_QuoteSession, testSymbol, ktype, sD, eD)
    # 登出帳號
    g_QuoteZMQ.Logout(g_QuoteSession)


if __name__ == '__main__':
    main()
