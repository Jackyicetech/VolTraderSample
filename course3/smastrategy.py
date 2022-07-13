import numpy as np
import talib
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf

# 讀取歷史資料
history_data = pd.read_csv("history_data.csv", index_col="Date", parse_dates=True)

# 設定起始資金
cash = 100000

# 設定各項初始參數及列表
# 計算策略賺錢的次數
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
# 投資報酬率
ROI = []
# 買進賣出訊號點
up_markers = []
down_markers = []
# 設定tick倍率
tick_price = 200
# 設定手續費
fees = 50
# 是否持倉，0代表沒有，1則是有持倉
pos = 0

# 計算均線
t1 = 5
t2 = 10
globals()['sma_' + str(t1)] = talib.SMA(history_data["Close"], timeperiod=t1)
globals()['sma_' + str(t2)] = talib.SMA(history_data["Close"], timeperiod=t2)

# 計算短期均線減長期均線的值
diff = globals()['sma_' + str(t1)] - globals()['sma_' + str(t2)]

for i in range(len(history_data["Close"])):
    if 1 < i < len(history_data["Close"]):
        # 如果前天的短期均線低於長期均線時以及昨天的短期均線高於長期均線時(黃金交叉)，並且當前沒有持倉的情況下就以今天的開盤價進行買入
        if diff[i - 1] > 0 > diff[i - 2] and pos == 0:
            buy_date.append(history_data.index[i])
            buyprice.append(history_data["Open"][i])

            # 開盤價-200的位置紀錄買入訊號點
            up_markers.append(history_data["Open"][i] - 200)
            # 投資報酬率及賣出點增加nan值
            ROI.append(np.nan)
            down_markers.append(np.nan)
            # 紀錄買入時的價格
            tick = history_data["Open"][i]
            # 買入後有持倉設為1
            pos = 1

        # 如果前天的短期均線高於長期均線且昨天的短期均線低於長期均線(死亡交叉)，或今天是最後一天，且在有持倉的情況下，今天就以開盤價的價格賣出
        elif (diff[i - 1] < 0 < diff[i - 2] or i == len(history_data["Close"]) - 1) and pos == 1:
            sell_date.append(history_data.index[i])
            sellprice.append(history_data["Open"][i])
            # 買進點增加nan
            up_markers.append(np.nan)
            # 開盤價+200的位置紀錄賣出訊號點
            down_markers.append(history_data["Open"][i] + 200)
            # 賣出後計算當前資金，1tick=200元，再扣掉買入及賣出各50元手續費
            cash += (history_data["Open"][i] - tick) * tick_price - 2 * fees
            # 將賣出後的現金數紀錄到cashlist列表中
            cashlist.append(cash)
            # 投資報酬率增加賣出價格減買入價格除以初始資金
            ROI.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
             # 賣出後沒有持倉，將pos設為0
            pos = 0
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

ROI_value = [x for x in ROI if np.isnan(x) == False]
d = [buy_date, buyprice, sell_date, sellprice, ROI_value]
df = pd.DataFrame(d, index=["買進日期", "買進價格", "賣出日期", "賣出價格", "投資報酬率"])
print(df.to_string())
print("最終投資報酬率:", sum(ROI_value))
print("最終持有資金:", cash)
print("勝率:", wincounts / len(sellprice))
print("賺賠比:", wintotal * losscounts / (wincounts * losstotal))

# 想要增加的圖表
added_plots = {"SMA" + str(t1): mpf.make_addplot(globals()['sma_' + str(t1)]),
               "SMA" + str(t2): mpf.make_addplot(globals()['sma_' + str(t2)]),
               "Buy": mpf.make_addplot(up_markers, type='scatter', marker='^', markersize=100),
               "Sell": mpf.make_addplot(down_markers, type='scatter', marker='v', markersize=100),
               "ROI": mpf.make_addplot(ROI, type='scatter', panel=2)
               }
# 設定圖表的顏色與網狀格格式
style = mpf.make_mpf_style(marketcolors=mpf.make_marketcolors(up="r", down="g", inherit=True),
                           gridcolor="gray")

# 畫K線和均線圖
fig, axes = mpf.plot(history_data, type="candle", style=style,
                     addplot=list(added_plots.values()),
                     volume=True,
                     returnfig=True)

# 設定圖例
axes[0].legend([None] * (len(added_plots) + 2))
handles = axes[0].get_legend().legendHandles
axes[0].legend(handles=handles[2:], labels=list(added_plots.keys()))

axes[0].set_ylabel("Price")
axes[2].set_ylabel("Volume")
axes[4].set_ylabel("ROI")
plt.show()
