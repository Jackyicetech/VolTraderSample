from typing import Any
from vnpy.trader.object import BarData
from vnpy.app.cta_strategy import (
    CtaTemplate,
    BarGenerator,
    ArrayManager
)
from vnpy.trader.constant import Direction
from vnpy.app.cta_strategy.backtesting import BacktestingEngine, OptimizationSetting
from datetime import datetime
import plotly.io as pio

pio.renderers.default = 'iframe'


class SMAStrategy(CtaTemplate):
    # 定義參數
    short_period = 10
    long_period = 20

    # 定義變數
    short_ma0 = 0.0
    short_ma1 = 0.0
    long_ma0 = 0.0
    long_ma1 = 0.0

    parameters = ["short_period", "long_period"]

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


def get_commission(cost, multiplier, qty, direction):
    commission = cost * multiplier * qty * (2 / 100000)
    fee = 50

    return commission + fee


engine = BacktestingEngine()
engine.set_parameters(
    vt_symbol='VolTrader.TFE',
    interval='d',
    start=datetime(2018, 1, 1),
    end=datetime(2022, 7, 1),
    rate=get_commission,  # 手續費
    slippage=2,  # 滑價
    size=200,  # 契約倍率
    pricetick=1,  # 價格變動單位
    capital=500_000,  # 回測本金
    collection_name='VolTrader'
)

settings = {
    'short_period': 12,
    'long_period': 24
}

engine.add_strategy(SMAStrategy, settings)
engine.load_data()
engine.run_backtesting()
df = engine.calculate_result()
engine.calculate_statistics()
engine.show_chart()

for trade in engine.get_all_trades():
    print(trade)
setting = OptimizationSetting()
setting.set_target("total_net_pnl") # total_net_pnl, sharpe_ratio
setting.add_parameter("short_period", 10, 20, 1)
setting.add_parameter("long_period", 20, 30, 1)

results = engine.run_optimization(setting)