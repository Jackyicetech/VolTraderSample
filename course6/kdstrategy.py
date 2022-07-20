import numpy as np
import talib
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
import statsmodels.api as sm
from statsmodels import regression
from prettytable import PrettyTable

# 讀取歷史資料
history_data = pd.read_csv("history_data.csv", index_col="Date", parse_dates=True)

# 設定各項初始參數及列表
# 計算策略賺錢的次數
wincounts = wintotal = losscounts = losstotal = 0
# 紀路起始資金與每次賣出後的現金數
# 設定起始資金
cash = 100000
cashlist = [cash]
# 買進日期及價格、賣出日期及價格
buy_date, buyprice, sell_date, sellprice = [], [], [], []
# 投資報酬率
ROI = []
# 銀行定期利率
riskfree = 0.009
equity = [cash, cash]
ROI_daily = []
# 買進賣出訊號點
up_markers, down_markers = [], []
# 設定tick倍率
tick_price = 200
# 設定手續費
fees = 50
# 是否持倉，0代表沒有，1則是有持倉
pos = 0
quantity = []
tdd = mdd = 0
DD = []
# 每筆買進時的價格
tick = 0
# 設定停損價格，如果當前價格低於買進時減停損價則進行賣出
stop_price = 10
# 紀錄總交易日
dates = 0
# 紀錄最大回徹天數
temp = count = 0

# 計算KD值
slowk, slowd = talib.STOCH(history_data['High'], history_data['Low'], history_data['Close'], fastk_period=9,
                           slowk_period=3, slowd_period=3)

# 計算K線減去D線的值
diff = slowk - slowd

for i in range(len(history_data["Close"])):
    if 1 < i:
        # 如果前天的K線低於D線時以及昨天的K線高於D線時(黃金交叉)，並且當前沒有持倉的情況下就以今天的開盤價進行買入，最後一天不進行買入
        if diff[i - 1] > 0 > diff[i - 2] and pos == 0 and i < len(history_data["Close"]):
            buy_date.append(history_data.index[i])
            buyprice.append(history_data["Open"][i])

            # 開盤價-200的位置紀錄買入訊號點
            up_markers.append(history_data["Open"][i] - 200)
            # 投資報酬率及賣出點增加nan值
            ROI.append(np.nan)
            down_markers.append(np.nan)
            # 紀錄買入時的價格
            tick = history_data["Open"][i]
            cashlist.append(cashlist[-1])
            # 買入後有持倉設為1
            pos = 1
            # 記錄總資產
            equity.append(equity[-1])
            # 紀錄每日投資報酬率
            ROI_daily.append((equity[-1] - equity[-2]) / equity[-2])
            # 紀錄買進口數
            quantity.append(1)
            # 買進時延續上一個tdd
            DD.append(tdd)

        # 如果前天的K線高於D線時以及昨天的K線低於D線時(死亡交叉)、下跌超過止損價或今天是最後一天，且在有持倉的情況下，今天就以開盤價的價格賣出
        elif (diff[i - 1] < 0 < diff[i - 2] or history_data["Close"][i - 1] <= (tick - stop_price) or i == len(
                history_data["Close"]) - 1) and pos == 1:
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
            # 投資報酬率增加賣出價格除以初始資金
            ROI.append((cashlist[-1] - cashlist[-2]) / cashlist[0])
            # 賣出後沒有持倉，將pos設為0
            pos = 0
            # 記錄總資產
            equity.append((history_data["Open"][i] - history_data["Open"][i - 1]) * tick_price + equity[-1])
            # 紀錄每日投資報酬率
            ROI_daily.append((equity[-1] - equity[-2]) / equity[-2])
            # 紀錄賣出口數
            quantity.append(-1)
            tdd += (history_data["Open"][i] - history_data["Open"][i - 1]) * tick_price / cashlist[0]
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
            if pos:
                equity.append((history_data["Open"][i] - history_data["Open"][i - 1]) * tick_price + equity[-1])
                ROI_daily.append((equity[-1] - equity[-2]) / equity[-2])

                tdd += (history_data["Open"][i] - history_data["Open"][i - 1]) * tick_price / cashlist[0]
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
        DD.append(0)

for i in range(len(sellprice)):
    if sellprice[i] > buyprice[i]:
        wincounts += 1
        wintotal += sellprice[i] - buyprice[i]
    else:
        losscounts += 1
        losstotal += sellprice[i] - buyprice[i]
    date = sell_date[i] - buy_date[i]
    dates += date.days

averge_win = wintotal / wincounts * tick_price / cashlist[0]
averge_loss = losstotal / losscounts * tick_price / cashlist[0]


def data(x, y):
    x = sm.add_constant(x)
    model = regression.linear_model.OLS(y, x).fit()
    return model.params[0], model.params[1]


alpha, beta = data(history_data["Open"], history_data["Open"])

ROI_value = [x for x in ROI if np.isnan(x) == False]
d = [buy_date + sell_date, ['Buy Market On Open'] * len(buy_date) + ['Sell Market On Open'] * len(sell_date),
     buyprice + sellprice,
     [None] * len(buy_date) + ROI_value]
df = pd.DataFrame(d, index=["Date", "Type", "Price", "ROI"]).T
df.sort_values("Date", inplace=True)
df["Quantity"] = quantity
print(df.to_string(index=False))

# 計算各種回測指標
earn_ratio = wincounts / len(sellprice)
odds = averge_win / abs(averge_loss)
annual_std = np.std(ROI_daily) * np.sqrt(len(ROI_daily)) / np.sqrt(cashlist[0])
sharp_ratio = (np.mean(ROI_daily) - riskfree) / np.std(ROI_daily) * np.sqrt(len(ROI_daily))
table = PrettyTable(["各項指標名稱", "數值"])

table.add_rows(rows=[["總投資報酬率(未扣手續費):", np.round(sum(ROI_value) + len(sell_date) * fees * 2 / cashlist[0], 4)],
                     ["淨投資報酬率(扣手續費):", np.round(sum(ROI_value), 4)],
                     ["總交易日:", dates],
                     ["起始資金:", cashlist[0]],
                     ["最終持有資金:", cash],
                     ["淨利潤:", cash - cashlist[0]],
                     ["勝率:", earn_ratio],
                     ["損失率:", 1 - earn_ratio],
                     ["平均獲利:", np.round(averge_win, 4)],
                     ["平均虧損:", np.round(averge_loss, 4)],
                     ["賺賠比:", np.round(odds, 4)],
                     ["期望值:", np.round(earn_ratio * odds - (1 - earn_ratio), 4)],
                     ["總交易次數:", len(buy_date) + len(sell_date)],
                     ["總手續費:", len(sell_date) * fees * 2],
                     ["最大資金回撤:", np.round(mdd, 4)],
                     ["最大回撤天數:", count],
                     ["日均盈虧:", np.round((cash - cashlist[0]) / dates, 4)],
                     ["日均手續費:", np.round(len(sell_date) * fees * 2 / dates, 4)],
                     ["日均成交金額:", np.round(sum(sellprice + buyprice) * tick_price / dates, 4)],
                     ["日均成交筆數:", np.round((len(buy_date) + len(sell_date)) / dates, 4)],
                     ["年化收益率:", np.round(sum(ROI_value) / 1.5, 4)],
                     ["年化標準差:", np.round(annual_std, 4)],
                     ["年化變異數:", np.round(annual_std ** 2, 4)],
                     ["年均複合增長率:", np.round((1 + sum(ROI_value)) ** (2 / 3) - 1, 4)],
                     ["Alpha:", np.round(alpha, 4)],
                     ["Beta:", np.round(beta, 4)],
                     ["Sharp Ratio:", np.round(sharp_ratio, 4)],
                     ["Treynor ratio:", np.round((np.mean(ROI_daily) - riskfree) / beta, 4)]])
table.align = "l"
print(table)

# 想要增加的圖表
added_plots = {
    "Buy": mpf.make_addplot(up_markers, type='scatter', marker='^', markersize=100),
    "Sell": mpf.make_addplot(down_markers, type='scatter', marker='v', markersize=100),
    "ROI": mpf.make_addplot(ROI, type='scatter', panel=2),
    "K": mpf.make_addplot(slowk, panel=3),
    "D": mpf.make_addplot(slowd, panel=3),
    "DD": mpf.make_addplot(DD, panel=4),
    "Equity": mpf.make_addplot(equity, panel=5)
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
axes[6].legend(labels=['K', 'D'])
axes[0].set_ylabel("Price")
axes[2].set_ylabel("Volume")
axes[4].set_ylabel("ROI")
axes[6].set_ylabel("KD")
axes[8].set_ylabel("DD")
axes[10].set_ylabel("Equity")
plt.show()
