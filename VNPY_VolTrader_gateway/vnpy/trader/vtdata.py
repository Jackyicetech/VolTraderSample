from datetime import timedelta, datetime
from typing import List, Optional
from pytz import timezone
from quote_functions import *
from numpy import ndarray
from tcoreapi_mq import *
from .constant import Interval
from .object import BarData, TickData, HistoryRequest

INTERVAL_VT2RQ = {
    Interval.MINUTE: "1K",
    Interval.TICK: "TICKS",
    Interval.DAILY: "DK",
}

TW_TZ = timezone("Asia/Taipei")


class VTdataClient:
    """
    Client for querying history data from VolTraderdata.
    """
    def __init__(self):
        self.g_QuoteSession = None
        self.q_data = None
        self.g_QuoteZMQ = None
        self.inited: bool = False
        self.symbols: ndarray = None

    def init(self) -> bool:
        self.inited = True
        return True

    def query_history(self, req: HistoryRequest) -> Optional[List[BarData]]:
        """
        Query history bar data from mcdata.
        """
        if not self.g_QuoteZMQ:
            self.g_QuoteZMQ = QuoteAPI("ZMQ", "8076c9867a372d2a9a814ae710c256e2")
            self.q_data = self.g_QuoteZMQ.Connect("51647")
            self.g_QuoteSession = self.q_data["SessionKey"]
        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        start = req.start
        end = req.end

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
                dt = datetime.strptime(str(his["Date"][i]) + "1500", datetime_format)
            else:
                dt = datetime.strptime(str(his["Date"][i]*10000+int(his["Time"][i]/100)),
                                       datetime_format)+timedelta(hours=8)

            dt = TW_TZ.localize(dt)
            open_interest = 0
            bar = BarData(
                symbol=symbol,
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
            bars.append(bar)
        self.g_QuoteZMQ.Logout(self.g_QuoteSession)
        self.g_QuoteZMQ = None
        return bars

    def query_tick_history(self, req: HistoryRequest) -> Optional[List[TickData]]:
        """
        Query history bar data from RQData.
        """
        pass


vtdata_client = VTdataClient()
