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
# 渲染格式設定
pio.renderers.default = 'iframe'
# 開始時間
start_time = datetime(2002, 1, 1)
# 結束時間
end_time = datetime(2022, 7, 15)
# 合約代碼
contract = "TC.F.TWF.TXF.HOT"
# 轉換後的合約代碼
contract_vnpy = contract.replace(".", "-")


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
                symbol=contract_vnpy,
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


class SMAStrategy(CtaTemplate):
    # 短周期
    short_period = 12
    # 長周期
    long_period = 24

    # 短周期均線暫存值
    short_ma0 = None
    short_ma1 = None
    # 長周期均線暫存值
    long_ma0 = None
    long_ma1 = None


    def __init__(
            self,
            cta_engine: Any,
            strategy_name: str,
            vt_symbol: str,
            setting: dict,
    ):
        # 呼叫父類別的初始化函式
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")

        self.load_bar(10)

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
        # 黃金交叉
        cross_over = (self.short_ma0 >= self.long_ma0 and
                      self.short_ma1 < self.long_ma1)
        # 死亡交叉
        cross_below = (self.short_ma0 <= self.long_ma0 and
                       self.short_ma1 > self.long_ma1)

        # 黃金交叉時進場
        if cross_over:
            if self.pos == 0:
                self.buy(bar.close_price, 1)
        # 死亡交叉出場
        elif cross_below:
            if self.pos > 0:
                self.sell(bar.close_price, 1)



if __name__ == '__main__':
    # 呼叫VTdataClient類別
    vtdata_client = VTdataClient()
    # 讀取歷史資料並儲存進資料庫
    vtdata_client.query_history(contract)
    # 設置VNPY回測引擎
    engine = BacktestingEngine()
    # 設置參數
    engine.set_parameters(
        vt_symbol=contract_vnpy+".LOCAL",
        interval=interval_setting,
        start=start_time,
        end=end_time,
        rate=0.00002,  # 交易稅
        slippage=2,  # 滑價
        size=200,  # 契約倍率
        pricetick=1,  # 價格變動單位
        capital=500_000  # 回測本金
    )
    # 策略參數設定
    settings = {}
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