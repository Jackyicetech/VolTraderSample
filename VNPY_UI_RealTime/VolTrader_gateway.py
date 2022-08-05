from copy import copy
from datetime import datetime
from typing import Dict
from tcoreapi_mq import *
import threading
import pytz
from vnpy.trader.constant import Exchange
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import (
    OrderRequest,
    CancelRequest,
    SubscribeRequest,
    TickData,
)

TW_TZ = pytz.timezone("Asia/Taipei")


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
        self.g_QuoteSession = ""
        self.q_data = None
        self.subscribed = set()
        self.ticks = {}
        self.g_QuoteZMQ = QuoteAPI("ZMQ", "8076c9867a372d2a9a814ae710c256e2")

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
        self.g_QuoteZMQ.Logout(self.g_QuoteSession)
        return

    def connect(self, setting: dict) -> None:
        """連接 VolTrader"""
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
                if message:
                    if message["DataType"] == "REALTIME":
                        if message['Quote']['TradeVolume']:
                            code = contract
                            tick = self.ticks.get(code, None)
                            dt = datetime.now()
                            if tick is None:
                                tick = TickData(
                                    symbol=code,
                                    exchange=exchange,
                                    name=f"{contract}",
                                    datetime=dt,
                                    gateway_name=self.gateway_name,
                                )
                            tick.datetime = dt
                            tick.volume = float(message['Quote']['TradeVolume'])
                            tick.last_price = float(message['Quote']['TradingPrice'])
                            tick.open_interest = 0
                            tick.open_price = float(message['Quote']['OpeningPrice'])
                            tick.high_price = float(message['Quote']['HighPrice'])
                            tick.low_price = float(message['Quote']['LowPrice'])
                            tick.bid_price_1 = float(message['Quote']['Bid'])
                            tick.bid_volume_1 = float(message['Quote']['BidVolume'])
                            tick.ask_price_1 = float(message['Quote']['Ask'])
                            tick.ask_volume_1 = float(message['Quote']['AskVolume'])
                            self.ticks[code] = tick
                            self.on_tick(copy(tick))

        t1 = threading.Thread(target=quote_sub_th, args=(self.g_QuoteZMQ, self.q_data["SubPort"],))
        t1.daemon = True
        t1.start()
        self.g_QuoteZMQ.SubQuote(self.g_QuoteSession, contract)

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        if req.symbol in self.subscribed:
            return
        if req.symbol:
            self.tick_data(req.symbol)
            self.write_log(f"訂閱 {req.symbol}")
            self.subscribed.add(req.symbol)

        else:
            self.write_log(f"無此訂閱合約[{req.symbol}].")

