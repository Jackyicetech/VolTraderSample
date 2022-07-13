import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import timedelta

# 讀取歷史資料
history_data = pd.read_csv("history_data.csv", index_col='Date_Time', parse_dates=[["Date", "Time"]])
history_data.index = pd.to_datetime(history_data.index + timedelta(hours=8))

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
fees = 50 / 2
# 是否持倉，0代表沒有，1則是有持倉
pos = 0
upper = []
middle = []
lower = []
# 每筆買進時的價格
tick = 0
# 設定停損價格，如果當前價格低於買進時減停損價則進行賣出
stop_price = 100
# 設定上一分K的最高最低價
last_low = history_data['Low']
last_high = history_data['High']

for i in range(len(history_data["Close"])):
    if 1 < i < len(history_data["Close"]):
        # 計算上關價和下關價
        upper.append(last_low[i - 1] + (last_high[i - 1] - last_low[i - 1]) * 1.382)
        middle.append((last_low[i - 1] + last_high[i - 1]) / 2)
        lower.append(last_high[i - 1] - (last_high[i - 1] - last_low[i - 1]) * 1.382)
        # 增加過濾條件
        if last_high[i - 1] - last_low[i - 1] >= 2:
            # 如果開盤價大於等於上關價並且沒有持倉則進行買入
            if history_data['Open'][i] >= upper[i] and pos == 0:
                buy_date.append(history_data.index[i])
                buyprice.append(history_data["Open"][i])

                # 開盤價-20的位置紀錄買入訊號點
                up_markers.append(history_data["Open"][i] - 20)
                # 投資報酬率及賣出點增加nan值
                ROI.append(np.nan)
                down_markers.append(np.nan)
                # 紀錄買入時的價格
                tick = history_data["Open"][i]
                # 買入後有持倉設為1
                pos = 1

            # 如果開盤價小於等於下關價並且有持倉的情況則進行賣出
            # i == len(history_data["Close"]) - 1
            elif (history_data['Open'][i] <= lower[i] or history_data['Open'][i] <= (tick - stop_price) or (
                    history_data.index[i - 1].hour, history_data.index[i - 1].minute) == (13, 44) or (
                          history_data.index[i - 1].hour, history_data.index[i - 1].minute) == (4, 59)) and pos == 1:
                sell_date.append(history_data.index[i])
                sellprice.append(history_data["Open"][i])
                # 買進點增加nan
                up_markers.append(np.nan)
                # 開盤價+200的位置紀錄賣出訊號點
                down_markers.append(history_data["Open"][i] + 20)
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
    else:
        # 其餘情況增加nan值
        ROI.append(np.nan)
        up_markers.append(np.nan)
        down_markers.append(np.nan)
        upper.append(np.nan)
        lower.append(np.nan)

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
print("最終持有資金:", cash)
if ROI_value:
    print("最終投資報酬率:", np.round(sum(ROI_value),4))
    print("勝率:", np.round(wincounts / len(sellprice),4))
    print("賺賠比:", np.round(wintotal * losscounts / (wincounts * losstotal),4))
# 想要增加的圖表
added_plots = {"Upper": mpf.make_addplot(upper),
               "Lower": mpf.make_addplot(lower),
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
