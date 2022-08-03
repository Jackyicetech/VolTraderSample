from datetime import timedelta, datetime
from typing import List, Optional
from pytz import timezone

from numpy import ndarray
import numpy as np
import time

from rqdatac.share.errors import AuthenticationFailed

from tcoreapi_mq import *
from .setting import SETTINGS
from .constant import Exchange, Interval
from .object import BarData, TickData, HistoryRequest
from .utility import round_to

INTERVAL_VT2RQ = {
    Interval.MINUTE: "1K",
    Interval.TICK: "TICKS",
    Interval.DAILY: "DK",
}

INTERVAL_ADJUSTMENT_MAP = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.TICK: timedelta(),
    Interval.DAILY: timedelta()  # no need to adjust for daily bar
}

CHINA_TZ = timezone("Asia/Shanghai")


class MCdataClient:
    """
    Client for querying history data from mcdata.
    """

    def __init__(self):
        """"""
        self.inited: bool = False
        self.symbols: ndarray = None
        self.TCoreAPI = None

    def init(self, username: str = "", password: str = "") -> bool:
        """"""

        if self.inited:
            return True

        try:
            self.TCoreAPI = TCoreZMQ(quote_port="51647", trade_port="51617")
        except (RuntimeError, AuthenticationFailed):
            return False

        self.inited = True
        return True

    def to_rq_symbol(self, symbol: str, exchange: Exchange) -> str:
        rq_symbol = symbol
        return rq_symbol

    def query_history(self, req: HistoryRequest) -> Optional[List[BarData]]:
        """
        Query history bar data from mcdata.
        """

        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        start = req.start
        end = req.end

        rq_symbol = self.to_rq_symbol(symbol, exchange)

        rq_interval = INTERVAL_VT2RQ.get(interval)
        if not rq_interval:
            return None
        # For adjust timestamp from bar close point (mcdata) to open point (VN Trader)
        adjustment = INTERVAL_ADJUSTMENT_MAP[interval]

        # For querying night trading period data
        # end += timedelta(1)
        his = self.TCoreAPI.SubHistory(rq_symbol, rq_interval, datetime.strftime(start, "%Y%m%d") + "00",
                                       datetime.strftime(end, "%Y%m%d") + "07")
        bars = []
        datetime_format = "%Y%m%d %H%M%S"
        i = 0
        for item in his:
            if not item:
                continue
            if datetime_format:
                if rq_interval == "DK":
                    dt = datetime.strptime(item["Date"] + " " + "150000", datetime_format)
                else:
                    dt = datetime.strptime(item["Date"] + " " + str(int(item["Time"])), datetime_format)+timedelta(hours=8)
            else:
                dt = datetime.fromisoformat(item["Date"] + " " + item["Time"])

            i = i + 1
            dt = CHINA_TZ.localize(dt)
            open_interest = 0
            bar = BarData(
                symbol=rq_symbol,
                exchange=req.exchange,
                datetime=dt,
                interval=interval,
                volume=float(item["Volume"]),
                open_price=float(item["Open"]),
                high_price=float(item["High"]),
                low_price=float(item["Low"]),
                close_price=float(item["Close"]),
                open_interest=float(open_interest),
                gateway_name="MC",
            )
            bars.append(bar)

        return bars

    def query_tick_history(self, req: HistoryRequest) -> Optional[List[TickData]]:
        """
        Query history bar data from RQData.
        """
        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        start = req.start
        end = req.end

        rq_symbol = self.to_rq_symbol(symbol, exchange)

        rq_interval = INTERVAL_VT2RQ.get(interval)
        if not rq_interval:
            return None
        # For adjust timestamp from bar close point (mcdata) to open point (VN Trader)
        adjustment = INTERVAL_ADJUSTMENT_MAP[interval]
        data: List[TickData] = []
        # For querying night trading period data
        end += timedelta(1)
        his = self.TCoreAPI.SubHistory(rq_symbol, rq_interval, datetime.strftime(start, "%Y%m%d") + "00",
                                       datetime.strftime(end + 1, "%Y%m%d") + "07")
        bars = []
        tz = timezone("Etc/GMT+0")
        datetime_format = "%Y%m%d %H%M%S"

        for item in his:
            if datetime_format:
                dt = datetime.strptime(item["Date"] + " " + item["FilledTime"], datetime_format)
            else:
                dt = datetime.fromisoformat(item["Date"] + " " + item["FilledTime"])
            dt = tz.localize(dt)
            open_interest = 0

            bar = TickData(
                symbol=symbol,
                exchange=exchange,
                datetime=dt,
                open_price=float(item["TradingPrice"]),
                high_price=float(item["TradingPrice"]),
                low_price=float(item["TradingPrice"]),
                pre_close=0,
                last_price=float(item["TradingPrice"]),
                volume=float(item["TradeQuantity"]),
                open_interest=float(item["OI"]),
                limit_up=0,
                limit_down=0,
                bid_price_1=float(item["Bid"]),
                bid_price_2=0.0,
                bid_price_3=0.0,
                bid_price_4=0.0,
                bid_price_5=0.0,
                ask_price_1=float(item["Ask"]),
                ask_price_2=0.0,
                ask_price_3=0.0,
                ask_price_4=0.0,
                ask_price_5=0.0,
                bid_volume_1=0.0,
                bid_volume_2=0.0,
                bid_volume_3=0.0,
                bid_volume_4=0.0,
                bid_volume_5=0.0,
                ask_volume_1=0.0,
                ask_volume_2=0.0,
                ask_volume_3=0.0,
                ask_volume_4=0.0,
                ask_volume_5=0.0,
                gateway_name="MC",
            )
            bars.append(bar)

        return bars


mcdata_client = MCdataClient()
