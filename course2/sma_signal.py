import talib
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf

# 讀取歷史資料
history_data = pd.read_csv("history_data.csv", index_col="Date", parse_dates=True)

# 計算均線
sma_15 = talib.SMA(history_data["Close"], timeperiod=15)
sma_30 = talib.SMA(history_data["Close"], timeperiod=30)

# 想要增加的圖表
added_plots = {"SMA15": mpf.make_addplot(sma_15),
               "SMA30": mpf.make_addplot(sma_30)
               }
# 設定圖表的顏色與網狀格格式
style = mpf.make_mpf_style(marketcolors=mpf.make_marketcolors(up="r", down="g"),
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

plt.show()
