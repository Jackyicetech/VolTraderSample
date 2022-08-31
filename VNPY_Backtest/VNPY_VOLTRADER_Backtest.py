from typing import Any, List, Optional
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.database import get_database
from vnpy_ctastrategy import (
    CtaTemplate,
    BarGenerator,
    ArrayManager
)
from vnpy_ctastrategy.backtesting import BacktestingEngine, OptimizationSetting
from datetime import datetime, timedelta
from numpy import ndarray
from tcoreapi_mq import *
from quote_functions import *
import plotly.io as pio

# 時間種類轉換
INTERVAL_VT2RQ = {
    Interval.MINUTE: "1K",
    Interval.TICK: "TICKS",
    Interval.DAILY: "DK",
}
# 時間週期
interval_setting = Interval.DAILY
# 圖片格式
pio.renderers.default = 'iframe'
# 開始時間
start_time = datetime(2002, 1, 1)
# 結束時間
end_time = datetime(2022, 7, 15)
# 合約代碼
contract = "TC.F.TWF.TXF.HOT"


class VTdataClient:
    """
    串接VolTrader歷史資料的類別
    """
    def __init__(self):
        self.g_QuoteSession = None
        self.q_data = None
        self.g_QuoteZMQ = None
        self.symbols: ndarray = None

    def query_history(self, req: str) -> Optional[List[BarData]]:
        """
        請求VolTrader歷史資料的函式
        """
        if not self.g_QuoteZMQ:
            # 重新串接VolTrader
            self.g_QuoteZMQ = QuoteAPI("ZMQ", "8076c9867a372d2a9a814ae710c256e2")
            self.q_data = self.g_QuoteZMQ.Connect("51647")
            self.g_QuoteSession = self.q_data["SessionKey"]
        # 合約代碼
        symbol = req
        # 交易所
        exchange = Exchange.LOCAL
        # 時間週期
        interval = interval_setting
        # 開始時間
        start = start_time
        # 結束時間
        end = end_time
        # 轉換時間週期
        rq_interval = INTERVAL_VT2RQ.get(interval)
        if not rq_interval:
            return None

        # 建立一個行情執行緒
        t1 = threading.Thread(target=quote_sub_th, args=(self.g_QuoteZMQ, self.q_data["SubPort"],))
        t1.daemon = True
        t1.start()
        his = GetHistory(self.g_QuoteZMQ, self.g_QuoteSession, symbol, rq_interval,
                         datetime.strftime(start, "%Y%m%d") + "00",
                         datetime.strftime(end, "%Y%m%d") + "23")
        bars = []
        datetime_format = "%Y%m%d%H%M"
        for i in his.index:
            if rq_interval == "DK":
                # 日資料
                dt = datetime.strptime(str(his["Date"][i]) + "1500", datetime_format)
            else:
                # 分或Tick資料
                dt = datetime.strptime(str(his["Date"][i]*10000+int(his["Time"][i]/100)),
                                       datetime_format)+timedelta(hours=8)

            open_interest = 0
            # VNPY格式的資料
            bar = BarData(
                symbol="test",
                exchange=exchange,
                datetime=dt,
                interval=interval,
                volume=float(his["Volume"][i]),
                open_price=float(his["Open"][i]),
                high_price=float(his["High"][i]),
                low_price=float(his["Low"][i]),
                close_price=float(his["Close"][i]),
                open_interest=float(open_interest),
                gateway_name="VolTrader",
            )
            # 所有資料儲存進料表中
            bars.append(bar)
        # 儲存進資料庫
        database= get_database()
        database.save_bar_data(bars)
        # 登出
        self.g_QuoteZMQ.Logout(self.g_QuoteSession)
        self.g_QuoteZMQ = None
        # return bars


vtdata_client = VTdataClient()
vtdata_client.query_history(contract)


class SMAStrategy(CtaTemplate):
    # 定義參數
    short_period = 10
    long_period = 20

    # 定義變數
    short_ma0 = 0.0
    short_ma1 = 0.0
    long_ma0 = 0.0
    long_ma1 = 0.0
    # 參數名
    parameters = ["short_period", "long_period"]
    # 變數名
    variables = ["short_ma0", "short_ma1", "long_ma0", "long_ma1"]

    def __init__(
            self,
            cta_engine: Any,
            strategy_name: str,
            vt_symbol: str,
            setting: dict,
    ):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")

        self.load_bar(10)

    def on_start(self):
        """啟動"""
        self.write_log("策略啟動")

    def on_stop(self):
        """停止"""
        self.write_log("策略停止")

    def on_bar(self, bar: BarData):
        """K線更新"""

        am = self.am

        am.update_bar(bar)

        if not am.inited:
            return

        # 計算技術指標
        short_ma = am.sma(self.short_period, array=True)
        self.short_ma0 = short_ma[-1]
        self.short_ma1 = short_ma[-2]

        long_ma = am.sma(self.long_period, array=True)
        self.long_ma0 = long_ma[-1]
        self.long_ma1 = long_ma[-2]

        # 判斷均線交叉
        cross_over = (self.short_ma0 >= self.long_ma0 and
                      self.short_ma1 < self.long_ma1)

        cross_below = (self.short_ma0 <= self.long_ma0 and
                       self.short_ma1 > self.long_ma1)

        if cross_over:
            price = bar.close_price

            if self.pos == 0:
                self.buy(price, 1)

        elif cross_below:
            price = bar.close_price

            if self.pos > 0:
                self.sell(bar.close_price, 1)

        # 更新圖形介面
        self.put_event()


engine = BacktestingEngine()
engine.set_parameters(
    vt_symbol= "test.LOCAL",
    interval=interval_setting,
    start=start_time,
    end=end_time,
    rate=0.00002,  # 手續費
    slippage=2,  # 滑價
    size=200,  # 契約倍率
    pricetick=1,  # 價格變動單位
    capital=500_000  # 回測本金
)

settings = {
    'short_period': 12,
    'long_period': 24
}
# 添加策略
engine.add_strategy(SMAStrategy, settings)
# 讀取資料
engine.load_data()
# 執行回測
engine.run_backtesting()
df = engine.calculate_result()
# 計算統計指標
engine.calculate_statistics()
# 顯示回測績效圖表
engine.show_chart()

for trade in engine.get_all_trades():
    # 顯示交易時間、價格等資訊
    print(trade)

if __name__ == '__main__':
    # 參數優化設定
    setting = OptimizationSetting()
    # 最大化目標
    setting.set_target("total_net_pnl")  # total_net_pnl, sharpe_ratio
    # 參數範圍
    setting.add_parameter("short_period", 10, 20, 1)
    setting.add_parameter("long_period", 21, 30, 1)

    results = engine.run_bf_optimization(setting)
