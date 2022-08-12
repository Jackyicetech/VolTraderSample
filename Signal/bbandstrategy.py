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
from prettytable import PrettyTable
import statsmodels.api as sm
from statsmodels import regression

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
equity = [cash, cash]
# 投資報酬率
ROI = []
ROI_long = []
ROI_short = []
ROI_minute = []
tdd = mdd = 0
DD = []
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

for i in range(len(history_data["Close"])):
    if 0 < i < len(history_data["Close"]) - 1:
        # 如果上分鐘市場價高於下軌且這分鐘市場價又低於下軌，且在短均線皆大於長均線、沒有做多的情況下，或是空單價格上漲超過100點以上買進
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
            # 買入後有持倉設為1
            pos = 1
            # 記錄總資產
            equity.append((history_data["Open"][i] - history_data["Open"][i + 1]) *
                          tick_price + equity[-1])
            # 紀錄每分投資報酬率
            ROI_minute.append((equity[-1] - equity[-2]) / equity[-2])

            tdd += (history_data["Open"][i] - history_data["Open"][i + 1]) * tick_price / cashlist[0]
            if tdd > 0:
                tdd = 0
                temp = 0
            else:
                mdd = min(tdd, mdd)
                temp += 1
                count = max(temp, count)
            # 紀錄買入時的回撤值到回撤列表中
            DD.append(tdd)

        # 如果上分鐘市場價低於上軌且這分鐘市場價又高於上軌，且在短均線皆小於長均線、沒有做空的情況下，或是做多後上下跌超過100點賣出
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
                ROI.append(np.nan)
            # 紀錄空單進場時的價格
            tick = history_data["Open"][i + 1]
            # 買進點增加nan
            up_markers.append(np.nan)
            # 開盤價+20的位置紀錄賣出訊號點
            down_markers.append(history_data["High"][i + 1] + point)
            buyshort_date.append(history_data.index[i + 1])
            buyshortprice.append(history_data["Open"][i + 1])

            # 賣出後改為空單進場，將pos設為-1
            pos = -1
            # 記錄總資產
            equity.append((history_data["Open"][i + 1] - history_data["Open"][i]) *
                          tick_price + equity[-1])
            # 紀錄每日投資報酬率
            ROI_minute.append((equity[-1] - equity[-2]) / equity[-2])

            tdd += (history_data["Open"][i + 1] - history_data["Open"][i]) * tick_price / cashlist[0]
            if tdd > 0:
                tdd = 0
                temp = 0
            else:
                mdd = min(tdd, mdd)
                temp += 1
                count = max(temp, count)
            # 紀錄賣出時的回撤值到回撤列表中
            DD.append(tdd)

        else:
            if pos > 0:
                equity.append((history_data["Open"][i + 1] - history_data["Open"][i]) * tick_price + equity[-1])
                ROI_minute.append((equity[-1] - equity[-2]) / equity[-2])

                tdd += (history_data["Open"][i + 1] - history_data["Open"][i]) * tick_price / cashlist[0]
                if tdd > 0:
                    tdd = 0
                    temp = 0
                else:
                    mdd = min(tdd, mdd)
                    temp += 1
                    count = max(temp, count)
            elif pos < 0:
                equity.append((history_data["Open"][i] - history_data["Open"][i + 1]) * tick_price + equity[-1])
                ROI_minute.append((equity[-2] - equity[-1]) / equity[-2])

                tdd += (history_data["Open"][i] - history_data["Open"][i + 1]) * tick_price / cashlist[0]
                if tdd > 0:
                    tdd = 0
                    temp = 0
                else:
                    mdd = min(tdd, mdd)
                    temp += 1
                    count = max(temp, count)
            else:
                equity.append(equity[-1])
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

# 計算各種回測指標
averge_win = wintotal / wincounts * tick_price / cashlist[0]
averge_loss = losstotal / losscounts * tick_price / cashlist[0]
earn_ratio = wincounts / len(sellprice + sellshortprice)
odds = averge_win / averge_loss
annual_std = np.std(ROI_minute) * np.sqrt(len(ROI_minute)) / np.sqrt(cashlist[0])
dates = (max(sellshort_date[-1], sell_date[-1]) - min(buyshort_date[0], buy_date[0])).days
# 銀行定期利率
riskfree = 0.009 / 1440
sharp_ratio = (np.mean(ROI_minute) - riskfree) / np.std(ROI_minute)


def data(x, y):
    x = sm.add_constant(x)
    model = regression.linear_model.OLS(y, x).fit()
    return model.params[0], model.params[1]


alpha, beta = data(history_data["Open"], history_data["Open"])
table = PrettyTable(["各項指標名稱", "數值"])
table.add_rows(
    rows=[["總投資報酬率(未扣手續費):", np.round(sum(ROI_value) +
                                      len(sellshort_date + sell_date) * fees / cashlist[0], 4)],
          ["淨投資報酬率(扣手續費):", np.round(sum(ROI_value), 4)],
          ["總交易日:", dates],
          ["起始資金:", cashlist[0]],
          ["最終持有資金:", cash],
          ["淨利潤:", cash - cashlist[0]],
          ["勝率:", np.round(earn_ratio, 4)],
          ["損失率:", np.round(1 - earn_ratio, 4)],
          ["平均獲利:", np.round(averge_win, 4)],
          ["平均虧損:", np.round(averge_loss, 4)],
          ["賺賠比:", np.round(odds, 4)],
          ["期望值:", np.round(earn_ratio * odds - (1 - earn_ratio), 4)],
          ["總交易次數:", len(sellshort_date + sell_date)],
          ["總手續費:", len(sellshort_date + sell_date) * fees],
          ["最大資金回撤:", np.round(mdd, 4)],
          ["最大回撤天數:", np.round(count / 1440, 1)],
          ["日均盈虧:", np.round((cash - cashlist[0]) / dates, 4)],
          ["日均手續費:", np.round(len(sellshort_date + sell_date) * fees * 2 / dates, 4)],
          ["日均成交筆數:", np.round((len(sellshort_date + sell_date)) / dates, 4)],
          ["日均成交金額:", np.round(sum(sellprice + buyprice) * tick_price / dates, 4)],
          ["年化收益率:", np.round(sum(ROI_value) / (history_data.index[-1] -
                                                history_data.index[0]).days * 365, 4)],
          ["年化標準差:", np.round(annual_std, 4)],
          ["年化變異數:", np.round(annual_std ** 2, 4)],
          ["Alpha:", np.round(alpha, 4)],
          ["Beta:", np.round(beta, 4)],
          ["Sharp Ratio:", np.round(sharp_ratio, 4)],
          ["Treynor ratio:", np.round((np.mean(ROI_minute) - riskfree) / beta, 4)]])
table.align = "l"
print(table)
# 想要增加的圖表
added_plots = {"上軌": mpf.make_addplot(upperband),
               "中軌": mpf.make_addplot(middleband),
               "下軌": mpf.make_addplot(lowerband),
               "買入": mpf.make_addplot(up_markers, type='scatter', marker='^', markersize=200),
               "賣出": mpf.make_addplot(down_markers, type='scatter', marker='v', markersize=200),
               "ROI": mpf.make_addplot(ROI, type='scatter', panel=1),
               "DD": mpf.make_addplot(DD, panel=2),
               "Equity": mpf.make_addplot(equity, panel=3)
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
axes[4].set_ylabel("DD")
axes[6].set_ylabel("Equity")
plt.show()
