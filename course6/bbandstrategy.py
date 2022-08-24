# 載入 tcoreapi
from tcoreapi_mq import *
# 載入我們提供的行情 function
from quote_functions import *
import threading
import numpy as np
import talib
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
from prettytable import PrettyTable
from matplotlib.ticker import FuncFormatter

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

########行情#######
# 建立一個行情執行緒
t1 = threading.Thread(target=quote_sub_th, args=(g_QuoteZMQ, q_data["SubPort"],))
t1.daemon = True
t1.start()

# 設定合約代碼
testSymbol = 'TC.F.TWF.TXF.HOT'

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
# 買進賣出日期及價格
buy_date, buyprice, sell_date, sellprice = [], [], [], []
# 空單進出場日期及價格
buyshort_date, buyshortprice, sellshort_date, sellshortprice = [], [], [], []
equity = [cash, cash]
# 投資報酬率
ROI, ROI_long, ROI_short, ROI_minute = [], [], [], []
tdd = mdd = 0
DD = []
# 買進賣出訊號點
up_markers, down_markers = [], []
# 設定tick倍率
tick_price = 200
tick = 0
reverse_price = 100
# 設定手續費
fees = 50
# 是否持倉，0代表沒有，1則是有多單，-1是空單
pos = 0
# 繪圖時訊號點距離價格的位置
point = 1
# 紀錄最大回徹天數
temp = count = 0

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


def equity_mdd(tdd, mdd, temp, count, pos):
    if not pos:
        equity.append(equity[-1])
        return tdd, mdd, temp, count
    else:
        # 計算損益
        profit_or_loss = (history_data["Open"][i + 1] - history_data["Open"][i]) * tick_price * pos
    # 記錄總資產
    equity.append(profit_or_loss + equity[-1])
    # 紀錄每分投資報酬率
    ROI_minute.append((equity[-1] - equity[-2]) / equity[-2])

    tdd += profit_or_loss
    if tdd > 0:
        tdd = 0
        temp = 0
    else:
        mdd = min(tdd, mdd)
        temp += 1
        count = max(temp, count)
    return tdd, mdd, temp, count


for i in range(len(history_data["Close"])):
    if 0 < i < len(history_data["Close"]) - 1:
        # 如果上根K收盤價高於下軌且這根K收盤價又低於下軌，且在短均線皆大於長均線、沒有做多的情況下，或是空單價格上漲超過100點以上買進
        if diff2[i] < 0 < diff2[i - 1] and \
                sma0[i] > middleband[i] > sma1[i] > sma2[i] and pos <= 0 or \
                history_data["Open"][i] >= tick + reverse_price and pos == -1:
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
            # 開盤價-20的位置紀錄買入訊號點
            up_markers.append(history_data["Low"][i + 1] - point)
            # 賣出點增加nan
            down_markers.append(np.nan)
            tdd, mdd, temp, count = equity_mdd(tdd, mdd, temp, count, pos)
            # 多單進場，pos設為1
            pos = 1
            # 紀錄買入時的回撤值到回撤列表中
            DD.append(tdd)

        # 如果上根K收盤價低於上軌且這根K收盤價又高於上軌，且在短均線皆小於長均線、沒有做空的情況下，或是做多後上下跌超過100點賣出
        elif diff[i] > 0 > diff[i - 1] and \
                sma0[i] < middleband[i] < sma1[i] < sma2[i] and pos >= 0 or \
                history_data["Open"][i] <= tick - reverse_price and pos == 1:
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
            # 開盤價+20的位置紀錄賣出訊號點
            down_markers.append(history_data["High"][i + 1] + point)
            buyshort_date.append(history_data.index[i + 1])
            buyshortprice.append(history_data["Open"][i + 1])
            tdd, mdd, temp, count = equity_mdd(tdd, mdd, temp, count, pos)
            # 空單進場，將pos設為-1
            pos = -1
            # 紀錄賣出時的回撤值到回撤列表中
            DD.append(tdd)

        else:
            tdd, mdd, temp, count = equity_mdd(tdd, mdd, temp, count, pos)

            # 紀錄回撤值到回撤列表中
            DD.append(tdd)
            # 其餘情況增加nan值
            ROI.append(np.nan)
            up_markers.append(np.nan)
            down_markers.append(np.nan)
    else:
        # 其餘情況增加nan值
        ROI.append(np.nan)
        up_markers.append(np.nan)
        down_markers.append(np.nan)
        DD.append(tdd)

dates = 0
# 多單
for i in range(len(sellprice)):
    # 賣出價格比買入價格高的情況
    if sellprice[i] > buyprice[i]:
        wincounts += 1
        wintotal += sellprice[i] - buyprice[i]
    # 買入價格比賣出價格高的情況
    else:
        losscounts += 1
        losstotal += buyprice[i] - sellprice[i]
# 空單
for i in range(len(sellshortprice)):
    # 買入價格比賣出價格高的情況
    if buyshortprice[i] > sellshortprice[i]:
        wincounts += 1
        wintotal += buyshortprice[i] - sellshortprice[i]
    # 賣出價格比買入價格高的情況
    else:
        losscounts += 1
        losstotal += sellshortprice[i] - buyshortprice[i]

# 調整表格設定
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
ROI_value = [x for x in ROI if np.isnan(x) == False]
d = [["多單"] * len(buy_date) + ["空單"] * len(buyshort_date), buy_date + buyshort_date, buyprice + buyshortprice,
     sell_date + sellshort_date, sellprice + sellshortprice, ROI_long + ROI_short]
df = pd.DataFrame(d, index=["多空", "買進日期", "買進價格", "賣出日期", "賣出價格", "投資報酬率"]).T
df = df.sort_values("買進日期")
print(df.to_string(index=False))
print("最終持有資金:", cash)
# 計算各種回測指標
# 平均獲利
averge_win = wintotal / wincounts * tick_price / cashlist[0]
# 平均虧損
averge_loss = losstotal / losscounts * tick_price / cashlist[0]
# 勝率
earn_ratio = wincounts / len(sellprice + sellshortprice)
# 盈虧比
odds = averge_win / averge_loss
# 年化標準差
annual_std = np.std(ROI_minute) * np.sqrt(len(ROI_minute)) / np.sqrt(cashlist[0])
# 總交易日
dates = len(pd.bdate_range(min(buyshort_date[0], buy_date[0]),
                           max(sellshort_date[-1], sell_date[-1])))
# 總交易次數
trades = len(sellshort_date + sell_date)
# 指標名稱
signal = ["總投資報酬率(未扣手續費)", "淨投資報酬率(扣手續費)", "總交易日", "最終持有資金", "淨利潤",
          "勝率", "損失率", "平均獲利", "平均虧損", "盈虧比", "期望值", "總交易次數", "總手續費",
          "最大虧損", "最大資金回撤率", "最大回撤天數", "日均盈虧", "日均手續費", "日均成交筆數",
          "日均成交金額", "年化收益率", "年化標準差", "年化變異數"]
# 指標數值
values = [np.round(sum(ROI_value) + (2*trades+1) * fees / cashlist[0], 4),
          np.round(sum(ROI_value), 4),
          dates,
          cash,
          cash - cashlist[0],
          np.round(earn_ratio, 4),
          np.round(1 - earn_ratio, 4),
          np.round(averge_win, 4),
          np.round(averge_loss, 4),
          np.round(odds, 4),
          np.round(earn_ratio * odds - (1 - earn_ratio), 4),
          trades,
          (2*trades+1) * fees,
          np.round(mdd, 4),
          np.round(1 - min(equity) / cashlist[0], 4),
          np.round(count / 1140, 1),
          np.round((cash - cashlist[0]) / dates, 4),
          np.round((2*trades+1) * fees * 2 / dates, 4),
          np.round(trades / dates, 4),
          np.round(sum(sellprice + buyprice) * tick_price / dates, 4),
          np.round(sum(ROI_value) / (history_data.index[-1] - history_data.index[0]).days * 365, 4),
          np.round(annual_std, 4),
          np.round(annual_std ** 2, 4)]

table = PrettyTable(["各項指標名稱", "數值"])
for i in range(len(signal)):
    table.add_row([signal[i], values[i]])
# 預設表格數值置中
print(table)

_, (ax, ax2) = plt.subplots(2, 1, sharex=True)
# 畫回撤、總資產曲線
ax.plot(DD, color="grey")
ax2.plot(equity)


def format_date(index, pos):
    index = np.clip(int(index + 0.5), 0, len(history_data.index) - 1)
    return history_data.index[index].strftime("%Y-%m-%d")


ax.xaxis.set_major_formatter(FuncFormatter(format_date))
# 增加軸標籤
ax.set_ylabel("DD")
ax2.set_xlabel("Date")
ax2.set_ylabel("Equity")

plt.show()
