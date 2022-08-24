# 載入 tcoreapi
from tcoreapi_mq import *
# 載入我們提供的行情 function
from quote_functions import *
import threading
import numpy as np
import talib
import pandas as pd
from datetime import timedelta

# 建立 ZMQ 連線
# 設定連線授權碼，通常不用改。
g_QuoteZMQ = QuoteAPI("ZMQ", "8076c9867a372d2a9a814ae710c256e2")

# 設定連接 Port，通常不用改。
q_data = g_QuoteZMQ.Connect("51647")

print(q_data)

if q_data["Success"] != "OK":
    print("[ quote ]connection failed")

# 連線成功后，將取得的 Session Key 儲存下來，後面調用指令需要帶入。
g_QuoteSession = q_data["SessionKey"]

#############行情#############
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
sD = '2022062500'
eD = '2022072521'

# 顯示歷史數據
history_data = GetHistory(g_QuoteZMQ, g_QuoteSession, testSymbol, ktype, sD, eD)

history_data.index = pd.to_datetime(history_data["Date"] * 10000 + history_data["Time"] / 100,
                                    format='%Y%m%d%H%M') + timedelta(hours=8)
# 解除訂閱歷史數據
g_QuoteZMQ.UnsubHistory(g_QuoteSession, testSymbol, ktype, sD, eD)
# 登出帳號
g_QuoteZMQ.Logout(g_QuoteSession)

# 投資報酬率
ROI_list = []
# 勝率
winrate = []
# 賺賠比
winloss_list = []
# 參數值
params = []
# 初始資金十萬元
money = 100000


def Max_ROI(t1, t2=2, t3=2):
    # 設定各項初始參數及列表
    # 設定起始資金
    cash = money
    # 計算策略賺錢和賠錢的次數
    wincounts = 0
    wintotal = 0
    losscounts = 0
    losstotal = 0
    # 紀路起始資金與每次賣出後的現金數
    cashlist = [cash]
    # 買進日期及價格
    buy_date = []
    buyprice = []
    # 賣出日期及價格
    sell_date = []
    sellprice = []
    # 空單進場日期及價格
    buyshort_date = []
    buyshortprice = []
    # 空單出場日期及價格
    sellshort_date = []
    sellshortprice = []
    # 投資報酬率
    ROI = []
    ROI_long = []
    ROI_short = []
    # 買進賣出訊號點
    up_markers = []
    down_markers = []
    # 設定tick倍率
    tick_price = 200
    tick = 0

    # 設定手續費
    fees = 50
    # 是否持倉，0代表沒有，1則是有持倉
    pos = 0
    # 繪圖時訊號點距離價格的位置
    point = 1

    # 計算布林通道上中下三條線
    upperband, middleband, lowerband = talib.BBANDS(
        history_data["Close"], timeperiod=t1, nbdevup=t2, nbdevdn=t3, matype=0)
    # 均線種類:matype 0:SMA 1:EMA 2:WMA ...

    # 計算當前價格減去上軌跟下軌的值
    close_upper = history_data["Close"] - upperband
    close_lower = history_data["Close"] - lowerband

    for i in range(1, len(history_data["Close"]) - 1):

        # 如果上分鐘市場價高於下軌且這分鐘市場價又低於下軌，且在沒有做多的情況下，在下分鐘開盤時買進
        if close_lower[i] < 0 < close_lower[i - 1] and pos <= 0:
            if pos == -1:
                sellshort_date.append(history_data.index[i + 1])
                sellshortprice.append(history_data["Open"][i + 1])
                # 賣出後計算當前資金，1tick=200元，再扣掉買入及賣出各50元手續費
                cash += (tick - history_data["Open"][i + 1]) * tick_price - 2 * fees
                # 將賣出後的現金數紀錄到cashlist列表中
                cashlist.append(cash)
                # 投資報酬率增加賣出價格減買入價格除以初始資金
                ROI_short.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
                ROI.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
            else:
                # 多單進場手續費
                cash -= fees
                # 投資報酬率及賣出點增加nan值
                ROI.append(np.nan)

            # 紀錄買入時的價格
            tick = history_data["Open"][i + 1]
            buy_date.append(history_data.index[i + 1])
            buyprice.append(history_data["Open"][i + 1])
            # 紀錄買入訊號點
            up_markers.append(history_data["Low"][i + 1] - point)
            # 賣出點增加nan
            down_markers.append(np.nan)
            # 買入後有持倉設為1
            pos = 1

        # 如果上分鐘市場價低於上軌且這分鐘市場價又高於上軌，且在沒有做空的情況下，在下分鐘開盤時賣出
        elif close_upper[i] > 0 > close_upper[i - 1] and pos >= 0:
            if pos == 1:
                sell_date.append(history_data.index[i + 1])
                sellprice.append(history_data["Open"][i + 1])
                # 賣出後計算當前資金，1tick=200元，再扣掉買入及賣出各50元手續費
                cash += (history_data["Open"][i + 1] - tick) * tick_price - 2 * fees
                # 將賣出後的現金數紀錄到cashlist列表中
                cashlist.append(cash)
                # 投資報酬率增加賣出價格減買入價格除以初始資金
                ROI_long.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
                ROI.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
            else:
                # 空單進場手續費
                cash -= fees
                ROI.append(np.nan)
            # 紀錄空單進場時的價格
            tick = history_data["Open"][i + 1]
            # 買進點增加nan
            up_markers.append(np.nan)
            # 紀錄賣出訊號點
            down_markers.append(history_data["High"][i + 1] + point)
            buyshort_date.append(history_data.index[i + 1])
            buyshortprice.append(history_data["Open"][i + 1])

            # 賣出後改為空單進場，將pos設為-1
            pos = -1

        else:
            # 其餘情況增加nan值
            ROI.append(np.nan)
            up_markers.append(np.nan)
            down_markers.append(np.nan)

    for i in range(len(sellprice)):
        if sellprice[i] > buyprice[i]:
            wincounts += 1
            wintotal += sellprice[i] - buyprice[i]
        else:
            losscounts += 1
            losstotal += buyprice[i] - sellprice[i]
    for i in range(len(sellshortprice)):
        if buyshortprice[i] > sellshortprice[i]:
            wincounts += 1
            wintotal += buyshortprice[i] - sellshortprice[i]
        else:
            losscounts += 1
            losstotal += sellshortprice[i] - buyshortprice[i]
    ROI_value = [x for x in ROI if np.isnan(x) == False]
    print("最終持有資金:", cash)

    if ROI_value:
        print("最終投資報酬率:", np.round(sum(ROI_value), 4))
        print("勝率:", np.round(wincounts / len(sellprice + sellshortprice), 4))
        print("賺賠比:", np.round(wintotal * losscounts / (wincounts * losstotal), 4))
        ROI_list.append(np.round(sum(ROI_value), 4))
        winrate.append(np.round(wincounts / len(sellprice + sellshortprice), 4))
        winloss_list.append(np.round(wintotal * losscounts / (wincounts * losstotal), 4))
    else:
        ROI_list.append(0)
        winrate.append(0)
        winloss_list.append(0)


for mean in range(5, 30):
    for up_sigma in range(2, 3):
        for down_sigma in range(2, 3):
            print("\n參數為均線週期:%d,上標準差:%d,下標準差:%d" % (mean, up_sigma, down_sigma))
            Max_ROI(mean, up_sigma, down_sigma)
            params.append((mean, up_sigma, down_sigma))
# 紀錄最大化投資報酬率的參數值
index = ROI_list.index(max(ROI_list))
max_mean, max_up_sigma, max_down_sigma = params[index]
print('\n' * 2)
print("最優化參數均線回測結果為:")
print("最優參數為均線週期:%d,上標準差:%d,下標準差:%d" % (max_mean, max_up_sigma, max_down_sigma))
print("最終持有資金:", money * (1 + ROI_list[index]))
print("最終投資報酬率:", ROI_list[index])
print("勝率:", winrate[index])
print("賺賠比:", winloss_list[index])
opt = [[mean[0] for mean in params],
       [up_sigma[1] for up_sigma in params],
       [down_sigma[2] for down_sigma in params],
       winrate, winloss_list, ROI_list]
df = pd.DataFrame(opt, index=["均線週期", "上標準差數", "下標準差數", "勝率", "賺賠比", "投資報酬率"]).T
df["均線週期"] = df["均線週期"].astype(int)
df["上標準差數"] = df["上標準差數"].astype(int)
df["下標準差數"] = df["下標準差數"].astype(int)
df.index = df.index + 1
df.to_csv("優化結果.csv", index_label="參數編號")
