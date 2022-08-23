# 載入 tcoreapi
from tcoreapi_mq import *
# 載入我們提供的行情 function
from quote_functions import *
import threading
import numpy as np
import talib
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
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

# 設定各項初始參數及列表
# 設定起始資金
cash = 100000
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
reverse_price = 100
# 設定手續費
fees = 50
# 是否持倉，0代表沒有，1則是有持倉
pos = 0
# 繪圖時訊號點距離價格的位置
point = 1

# 計算布林通道上中下三條線
upperband, middleband, lowerband = talib.BBANDS(
    history_data["Close"], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
# 均線種類:matype 0:SMA 1:EMA 2:WMA ...
# 計算均線濾網
sma0 = talib.SMA(history_data["Close"], timeperiod=10)
sma1 = talib.SMA(history_data["Close"], timeperiod=50)
sma2 = talib.SMA(history_data["Close"], timeperiod=80)

# 計算當前價格減去上軌跟下軌的值
diff = history_data["Close"] - upperband
diff2 = history_data["Close"] - lowerband

for i in range(len(history_data["Close"])):
    if 0 < i < len(history_data["Close"])-1:
        # 如果上分鐘市場價高於下軌且這分鐘市場價又低於下軌，且在短均線皆大於長均線、沒有做多的情況下，或是空單價格上漲超過100點以上買進
        if diff2[i] < 0 < diff2[i - 1] and\
            sma0[i] > middleband[i] > sma1[i] > sma2[i] and pos <= 0 or\
                history_data["Open"][i] >= tick + reverse_price and pos == -1:
            if pos == -1:
                sellshort_date.append(history_data.index[i+1])
                sellshortprice.append(history_data["Open"][i+1])
                # 賣出後計算當前資金，1tick=200元，再扣掉買入時的手續費
                cash += (tick - history_data["Open"][i+1]) * tick_price - fees
                # 將賣出後的現金數紀錄到cashlist列表中
                cashlist.append(cash)
                # 投資報酬率增加賣出價格減買入價格除以初始資金
                ROI_short.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
                ROI.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
            else:
                # 投資報酬率及賣出點增加nan值
                ROI.append(np.nan)
            # 紀錄買入時的價格
            tick = history_data["Open"][i+1]
            buy_date.append(history_data.index[i+1])
            buyprice.append(history_data["Open"][i+1])
            # 開盤價-20的位置紀錄買入訊號點
            up_markers.append(history_data["Low"][i+1] - point)
            # 賣出點增加nan
            down_markers.append(np.nan)
            # 買入後有持倉設為1
            pos = 1

        # 如果上分鐘市場價低於上軌且這分鐘市場價又高於上軌，且在短均線皆小於長均線、沒有做空的情況下，或是做多後上下跌超過100點賣出
        elif diff[i] > 0 > diff[i - 1] and\
                sma0[i] < middleband[i] < sma1[i] < sma2[i] and pos >= 0 or\
                history_data["Open"][i] <= tick - reverse_price and pos == 1:
            if pos == 1:
                sell_date.append(history_data.index[i+1])
                sellprice.append(history_data["Open"][i+1])
                # 賣出後計算當前資金，1tick=200元，再扣掉賣出時的手續費
                cash += (history_data["Open"][i+1] - tick) * tick_price - fees
                # 將賣出後的現金數紀錄到cashlist列表中
                cashlist.append(cash)
                # 投資報酬率增加賣出價格減買入價格除以初始資金
                ROI_long.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
                ROI.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
            else:
                ROI.append(np.nan)
            # 紀錄空單進場時的價格
            tick = history_data["Open"][i+1]
            # 買進點增加nan
            up_markers.append(np.nan)
            # 開盤價+20的位置紀錄賣出訊號點
            down_markers.append(history_data["High"][i+1] + point)
            buyshort_date.append(history_data.index[i+1])
            buyshortprice.append(history_data["Open"][i+1])

            # 賣出後改為空單進場，將pos設為-1
            pos = -1

        else:
            # 其餘情況增加nan值
            ROI.append(np.nan)
            up_markers.append(np.nan)
            down_markers.append(np.nan)
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
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
ROI_value = [x for x in ROI if np.isnan(x) == False]
d = [buy_date, buyprice, sell_date, sellprice, ROI_long]
df = pd.DataFrame(d, index=["買進日期", "買進價格", "賣出日期", "賣出價格", "投資報酬率"]).T
d2 = [buyshort_date, buyshortprice, sellshort_date, sellshortprice, ROI_short]
df2 = pd.DataFrame(d2, index=["空單進場日期", "空單進場價格", "空單出場日期", "空單出場價格", "投資報酬率"]).T
print(df.to_string())
print(df2.to_string())
print("最終持有資金:", cash)

if ROI_value:
    print("最終投資報酬率:", np.round(sum(ROI_value), 4))
    print("勝率:", np.round(wincounts / len(sellprice + sellshortprice), 4))
    print("賺賠比:", np.round(wintotal * losscounts / (wincounts * losstotal), 4))

    # 想要增加的圖表
    added_plots = {"上軌": mpf.make_addplot(upperband),
                   "中軌": mpf.make_addplot(middleband),
                   "下軌": mpf.make_addplot(lowerband),
                   "買入": mpf.make_addplot(up_markers, type='scatter', marker='^', markersize=200),
                   "賣出": mpf.make_addplot(down_markers, type='scatter', marker='v', markersize=200),
                   "ROI": mpf.make_addplot(ROI,type='scatter', panel=1)
                   }
    # 設定圖表的顏色與網狀格格式
    style = mpf.make_mpf_style(marketcolors=mpf.make_marketcolors(up="r", down="g", inherit=True),
                               gridcolor="gray")

    # 畫布林線和成交量
    fig, axes = mpf.plot(history_data, type="candle", style=style,
                         addplot=list(added_plots.values()),
                         returnfig=True)

    # 設定圖例
    axes[0].legend([None] * (len(added_plots) + 2))
    handles = axes[0].get_legend().legendHandles
    axes[0].legend(handles=handles[2:], labels=list(added_plots.keys()))

    axes[0].set_ylabel("Price")
    axes[2].set_ylabel("ROI")
    plt.show()

    series = np.array(ROI)
    mask = np.isfinite(series)
    plt.plot(np.array(history_data.index)[mask], series[mask])
    plt.show()
