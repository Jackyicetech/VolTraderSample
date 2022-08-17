from datetime import timedelta, datetime
from typing import Dict, Optional, List
from tcoreapi_mq import *
from quote_functions import *
import threading
from vnpy.trader.constant import Exchange, Interval, Product
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import (
    OrderRequest,
    CancelRequest,
    SubscribeRequest,
    TickData,
    BarData,
    HistoryRequest,
    ContractData
)

INTERVAL_VT2RQ = {
    Interval.MINUTE: "1K",
    Interval.TICK: "TICKS",
    Interval.DAILY: "DK",
}


class VolTraderGateway(BaseGateway):
    """
     VolTrader for VeighNa Gateway
    """

    default_name: str = "VolTrader"
    default_setting: Dict[str, str] = {
        "quote_port": "51647",
    }

    exchanges = list({Exchange.LOCAL: "LOCAL"})

    def __init__(self, event_engine, gateway_name: str) -> None:
        """初始化"""
        super().__init__(event_engine, gateway_name)
        self.contracts: Dict[str, ContractData] = {}
        self.g_QuoteZMQ = None
        self.g_QuoteSession = ""
        self.q_data = None
        self.subscribed = set()
        self.ticks = {}
        self.gateway_name: str = gateway_name

    def cancel_order(self, req: CancelRequest) -> None:
        """委託撤單"""
        pass

    def query_account(self) -> None:
        """查詢資金"""
        pass

    def query_position(self) -> None:
        """查詢持倉"""
        pass

    def send_order(self, req: OrderRequest) -> str:
        """委託下單"""
        pass

    def close(self) -> None:
        """關閉接口"""
        if self.g_QuoteZMQ:
            self.g_QuoteZMQ.Logout(self.g_QuoteSession)
        return

    def connect(self, setting: dict) -> None:
        """連接 VolTrader"""
        self.g_QuoteZMQ = QuoteAPI("ZMQ", "8076c9867a372d2a9a814ae710c256e2")
        port: str = setting["quote_port"]
        self.q_data = self.g_QuoteZMQ.Connect(port)
        self.g_QuoteSession = self.q_data["SessionKey"]
        self.write_log(f"成功連接VolTrader")

    def tick_data(self, contract, exchange=Exchange.LOCAL):
        # 行情消息接收
        def quote_sub_th(obj, sub_port, filter=""):
            socket_sub = obj.context.socket(zmq.SUB)
            # socket_sub.RCVTIMEO=7000   #ZMQ超時時間設定
            socket_sub.connect("tcp://127.0.0.1:%s" % sub_port)
            socket_sub.setsockopt_string(zmq.SUBSCRIBE, filter)
            while True:
                message = (socket_sub.recv()[:-1]).decode("utf-8")
                index = re.search(":", message).span()[1]  # filter
                message = message[index:]
                message = json.loads(message)
                if message and message["DataType"] == "REALTIME" and message['Quote']['TradeVolume']:
                    dt = datetime.now()
                    contract_symbol = message['Quote']["Symbol"]
                    sign = "-"
                    contract_symbol = sign.join(contract_symbol.split("."))
                    tick = TickData(
                        symbol=contract_symbol,
                        exchange=exchange,
                        name=f"{contract_symbol}",
                        datetime=dt,
                        gateway_name=self.gateway_name,
                        volume=float(message['Quote']['TradeVolume']),
                        last_price=float(message['Quote']['TradingPrice']),
                        open_interest=0,
                        open_price=float(message['Quote']['OpeningPrice']),
                        high_price=float(message['Quote']['HighPrice']),
                        low_price=float(message['Quote']['LowPrice']),
                        bid_price_1=float(message['Quote']['Bid']),
                        bid_volume_1=float(message['Quote']['BidVolume']),
                        ask_price_1=float(message['Quote']['Ask']),
                        ask_volume_1=float(message['Quote']['AskVolume'])
                    )
                    self.ticks[contract_symbol] = tick
                    self.on_tick(tick)

        t1 = threading.Thread(target=quote_sub_th, args=(self.g_QuoteZMQ, self.q_data["SubPort"],))
        t1.daemon = True
        t1.start()
        sign = "."
        contract = sign.join(contract.split("-"))
        self.g_QuoteZMQ.SubQuote(self.g_QuoteSession, contract)

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        if req.symbol in self.subscribed:
            return
        if req.symbol:
            self.query_contract(req)
            self.tick_data(req.symbol)
            self.write_log(f"訂閱 {req.symbol}")
            self.subscribed.add(req.symbol)

        else:
            self.write_log(f"無此訂閱合約[{req.symbol}].")

    def query_history(self, req: HistoryRequest) -> Optional[List[BarData]]:
        """
        Query history bar data from VolTrader data.
        """
        sign = "."
        symbol = sign.join(req.symbol.split("-"))
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
                dt = datetime.strptime(str(his["Date"][i] * 10000 + int(his["Time"][i] / 100)),
                                       datetime_format) + timedelta(hours=8)

            open_interest = 0
            bar = BarData(
                symbol=req.symbol,
                exchange=exchange,
                datetime=dt - timedelta(minutes=1),
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
        return bars

    def query_contract(self, req: SubscribeRequest):
        contract: ContractData = ContractData(
            symbol=req.symbol,
            exchange=Exchange("LOCAL"),
            name=req.symbol,
            history_data=True,
            size=200,
            pricetick=0.01,
            product=Product.FUTURES,
            gateway_name=self.gateway_name
        )
        self.on_contract(contract)

# TC.F.TWF.TXF.HOT
# TC-F-TWF-TXF-HOT
