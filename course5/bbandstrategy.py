import numpy as np
import talib
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import timedelta

# 讀取歷史資料
history_data = pd.read_csv("history_data.csv", index_col='Date_Time', parse_dates=[["Date", "Time"]])
history_data.index = history_data.index + timedelta(hours=8)

# 設定各項初始參數及列表
# 設定起始資金
cash = 100000
# 計算策略賺錢和輸錢的次數
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
# 買空日期及價格
buyshort_date = []
buyshortprice = []
# 賣空日期及價格
sellshort_date = []
sellshortprice = []
# 投資報酬率
ROI = []
ROI_long = []
ROI_short = []
# 買進賣出訊號點
up_markers = []
down_markers = []
upshort_markers = []
downshort_markers = []
# 設定tick倍率
tick_price = 200
# 設定手續費(當沖手續費減半)
fees = 50 / 2
# 是否持倉，0代表沒有，1則是有持倉
pos = 0

# 計算布林通道上中下三條線
upperband, middleband, lowerband = talib.BBANDS(history_data["Close"], timeperiod=50, nbdevup=2, nbdevdn=2, matype=0)
# 均線種類:matype 0:SMA 1:EMA 2:WMA ...

# 計算當前價格減去上軌跟下軌的值
diff = history_data["Close"] - upperband
diff2 = history_data["Close"] - lowerband
diff3 = history_data["Close"] - middleband

for i in range(len(history_data["Close"])):
    if 1 < i < len(history_data["Close"]):
        # 如果上軌減去下軌的值不到20點，代表價格在小範圍波動不進行買賣
        if upperband[i - 1] - lowerband[i - 1] >= 20:
            # 如果上分鐘市場價低於上軌且這分鐘市場價又高於上軌，且在沒有持倉的情況下，則在下分鐘進行買入的動作，同樣套用到下軌上
            if (diff[i - 1] > 0 > diff[i - 2] or diff2[i - 1] > 0 > diff2[i - 2]) and pos == 0:
                buy_date.append(history_data.index[i])
                buyprice.append(history_data["Open"][i])
                # 開盤價-20的位置紀錄買入訊號點
                up_markers.append(history_data["Open"][i] - 20)
                # 投資報酬率及賣出點增加nan值
                upshort_markers.append(np.nan)
                downshort_markers.append(np.nan)
                ROI.append(np.nan)
                down_markers.append(np.nan)
                # 紀錄買入時的價格
                tick = history_data["Open"][i]
                # 買入後有持倉設為1
                pos = 1

            # 如果上分鐘市場價高於上軌且這分鐘市場價又低於上軌，且在有持倉的情況下，則在下分鐘進行賣出的動作，同樣套用到下軌上，或是有持倉即將閉市進行賣出
            elif (diff[i - 1] < 0 < diff[i - 2] or diff2[i - 1] < 0 < diff2[i - 2] or i == len(
                    history_data["Close"]) - 1) and pos == 1:
                sell_date.append(history_data.index[i])
                sellprice.append(history_data["Open"][i])
                # 買進點增加nan
                up_markers.append(np.nan)
                upshort_markers.append(np.nan)
                downshort_markers.append(np.nan)
                # 開盤價+20的位置紀錄賣出訊號點
                down_markers.append(history_data["Open"][i] + 20)
                # 賣出後計算當前資金，1tick=200元，再扣掉買入及賣出各50元手續費
                cash += (history_data["Open"][i] - tick) * tick_price - 2 * fees
                # 將賣出後的現金數紀錄到cashlist列表中
                cashlist.append(cash)
                # 投資報酬率增加賣出價格除以初始資金
                ROI_long.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
                ROI.append((cashlist[-1] - cashlist[-2]) / cashlist[0])

                # 賣出後沒有持倉，將pos設為0
                pos = 0
            # 如果價格由高往低穿過中軌，則進行放空
            elif diff3[i - 1] < 0 < diff3[i - 2] and pos == 0:
                buyshort_date.append(history_data.index[i])
                buyshortprice.append(history_data["Open"][i])
                # 開盤價-20的位置紀錄買入訊號點
                upshort_markers.append(history_data["Open"][i] - 20)
                # 投資報酬率及賣出點增加nan值
                up_markers.append(np.nan)
                down_markers.append(np.nan)
                ROI.append(np.nan)
                downshort_markers.append(np.nan)
                # 紀錄買入時的價格
                tick = history_data["Open"][i]
                # 買入後有持倉設為1
                pos = -1

            # 如果價格由低往高穿過中軌或是穿過下軌都進行賣空的動作，如果已經是閉市前最後一筆也要平倉
            elif (history_data["Close"][i - 1] >= middleband[i - 1] or history_data["Close"][i - 1] <= lowerband[
                i - 1] or i == len(
                    history_data["Close"]) - 1) and pos == -1:

                sellshort_date.append(history_data.index[i])
                sellshortprice.append(history_data["Open"][i])
                # 買進點增加nan
                upshort_markers.append(np.nan)
                # 開盤價+20的位置紀錄賣出訊號點
                downshort_markers.append(history_data["Open"][i] + 20)
                up_markers.append(np.nan)
                down_markers.append(np.nan)
                # 賣出後計算當前資金，1tick=200元，再扣掉買入及賣出各50元手續費
                cash += (tick - history_data["Open"][i]) * tick_price - 2 * fees
                # 將賣出後的現金數紀錄到cashlist列表中
                cashlist.append(cash)
                # 投資報酬率增加賣出價格減買入價格除以初始資金
                ROI_short.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
                ROI.append((cashlist[-1] - cashlist[-2]) / cashlist[0])

                # 賣出後沒有持倉，將pos設為0
                pos = 0
            else:
                # 其餘情況增加nan值
                upshort_markers.append(np.nan)
                downshort_markers.append(np.nan)
                ROI.append(np.nan)
                up_markers.append(np.nan)
                down_markers.append(np.nan)
        else:
            # 其餘情況增加nan值
            upshort_markers.append(np.nan)
            downshort_markers.append(np.nan)
            ROI.append(np.nan)
            up_markers.append(np.nan)
            down_markers.append(np.nan)
    else:
        # 其餘情況增加nan值
        upshort_markers.append(np.nan)
        downshort_markers.append(np.nan)
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
d = [buy_date, buyprice, sell_date, sellprice, ROI_long]
df = pd.DataFrame(d, index=["買進日期", "買進價格", "賣出日期", "賣出價格","投資報酬率"])
d2 = [buyshort_date,buyshortprice,sellshort_date,sellshortprice,ROI_short]
df2 = pd.DataFrame(d2, index=["買空日期", "買空價格", "賣空日期", "賣空價格","投資報酬率"])
print(df.to_string())
print(df2.to_string())
print("最終持有資金:", cash)
if ROI_value:
    print("最終投資報酬率:", np.round(sum(ROI_value),4))
    print("勝率:", np.round(wincounts / len(sellprice),4))
    print("賺賠比:", np.round(wintotal * losscounts / (wincounts * losstotal),4))

    # 想要增加的圖表
    added_plots = {"Upperband": mpf.make_addplot(upperband),
                   "Middleband": mpf.make_addplot(middleband),
                   "Lowereband": mpf.make_addplot(lowerband),
                   "Buy": mpf.make_addplot(up_markers, type='scatter', marker='^', markersize=100),
                   "Sell": mpf.make_addplot(down_markers, type='scatter', marker='v', markersize=100),
                   "Short": mpf.make_addplot(upshort_markers, type='scatter', marker='^', markersize=100, color='y'),
                   "Cover": mpf.make_addplot(downshort_markers, type='scatter', marker='v', markersize=100, color='k'),
                   "ROI": mpf.make_addplot(ROI, type='scatter', panel=2)
                   }
    # 設定圖表的顏色與網狀格格式
    style = mpf.make_mpf_style(marketcolors=mpf.make_marketcolors(up="r", down="g", inherit=True),
                               gridcolor="gray")

    # 畫布林線和成交量
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
