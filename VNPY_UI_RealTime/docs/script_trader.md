# ScriptTrader - 脚本策略交易模块

## 功能简介

ScriptTrader是用于**脚本策略交易**的功能模块，提供了交互式的量化分析和程序化交易功能，又提供以整个策略连续运行的脚本策略功能。

故其可视为直接利用Python对交易客户端进行操作。它与CTA策略模块的区别在于：

- 突破了单交易所，单标的的限制；
- 可以较方便的实现如股指期货和一篮子股票之间的对冲策略、跨品种套利、股票市场扫描自动化选股等功能。

## 加载启动

### VeighNa Station加载

启动登录VeighNa Station后，点击【交易】按钮，在配置对话框中的【应用模块】栏勾选【ScriptTrader】。

### 脚本加载

在启动脚本中添加如下代码：

```python 3
# 写在顶部
from vnpy_scripttrader import ScriptTraderApp

# 写在创建main_engine对象后
main_engine.add_app(ScriptTraderApp)
```

## 启动模块

在启动模块之前，请先连接交易接口（连接方法详见基本使用篇的连接接口部分）。看到VeighNa Trader主界面【日志】栏输出“合约信息查询成功”之后再启动模块，如下图所示：

![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/cta_strategy/1.png)

请注意，IB接口因为登录时无法自动获取所有的合约信息，只有在用户手动订阅行情时才能获取。因此需要在主界面上先行手动订阅合约行情，再启动模块。

成功连接交易接口后，在菜单栏中点击【功能】-> 【脚本策略】，或者点击左侧按钮栏的图标：

![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/0.png)

即可进入脚本交易模块的UI界面，如下图所示：

![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/1.png)

如果配置了数据服务（配置方法详见基本使用篇的全局配置部分），打开脚本交易模块时会自动执行数据服务登录初始化。若成功登录，则会输出“数据服务初始化成功”的日志，如下图所示：

![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/20.png)

用户可以通过UI界面使用以下功能：

### 启动

脚本策略需要事先编写好脚本策略文件，如test_strategy.py（脚本策略模板可参考[**脚本策略**](#jump)部分），因此点击【打开】按钮后需要用户指定该脚本策略文件的路径，如下图所示：

![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/21.png)

打开脚本策略之后，点击【启动】按钮则会启动脚本策略，并在下方界面输出相关信息，如下图所示：

![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/8.png)

### 停止

如果想停止脚本策略，直接点击【停止】按钮，之后策略会停止，通知会在下方界面输出“策略交易脚本停止”的日志，如下图所示：

![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/11.png)

### 清空

如果觉得下方显示界面的信息太多，或者想开启新的脚本策略，可以点击【清空】按钮，这时下方的所有信息就会被清空，如下图所示：

![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/10.png)


## 脚本策略模板

<span id="jump">

脚本策略文件编写需要遵循一定格式，下面提供使用模板，其作用为：

- 订阅两个品种的行情；
- 打印合约信息；
- 每隔3秒获取最新行情。

```python 3
from time import sleep
from vnpy_scripttrader import ScriptEngine

def run(engine: ScriptEngine):
    """"""
    vt_symbols = ["sc2209.INE", "sc2203.INE"]

    # 订阅行情
    engine.subscribe(vt_symbols)

    # 获取合约信息
    for vt_symbol in vt_symbols:
        contract = engine.get_contract(vt_symbol)
        msg = f"合约信息，{contract}"
        engine.write_log(msg)

    # 持续运行，使用strategy_active来判断是否要退出程序
    while engine.strategy_active:
        # 轮询获取行情
        for vt_symbol in vt_symbols:
            tick = engine.get_tick(vt_symbol)
            msg = f"最新行情, {tick}"
            engine.write_log(msg)

        # 等待3秒进入下一轮
        sleep(3)
```

其中engine.strategy_active用于控制While循环，可视作是脚本策略的开关：

- 点击【启动】按钮，启动While循环，执行脚本策略；
- 点击【停止】按钮，退出While循环，停止脚本策略。


## 功能函数

Jupyter模式是基于脚本引擎（ScriptEngine）驱动的，下面通过jupyter notebook来说明ScriptEngine引擎的各功能函数。

首先打开Jupyter notebook，然后加载组件、初始化脚本引擎：

```python 3
from vnpy_scripttrader import init_cli_trading
from vnpy_ctp import CtpGateway
engine = init_cli_trading([CtpGateway])
```

其中：

- 脚本引擎可以支持同时连接多个接口；
- init_cli_trading(gateways: Sequence[BaseGateway])可以将多个接口类，以列表的形式传递给init_cli_trading；
- init_cli_trading可视为vnpy封好的初始化启动函数，对主引擎、脚本引擎等各种对象进行了封装。

### 连接接口

**connect_gateway**

* 入参：setting: dict, gateway_name: str

* 出参：无

不同接口需要不同的配置参数，SimNow的配置如下：
```json
setting = {
    "用户名": "xxxx",
    "密码": "xxxx",
    "经纪商代码": "9999",
    "交易服务器":"180.168.146.187:10202",
    "行情服务器":"180.168.146.187:10212",
    "产品名称":"simnow_client_test",
    "授权编码":"0000000000000000"
}
engine.connect_gateway(setting,"CTP")
```

其他接口配置可以参考site-packages目录下不同接口模块类（如vnpy_ctp.gateway.ctp_gateway）中的default_setting来填写。

### 订阅行情

**subscribe**

* 入参：vt_symbols: Sequence[str]

* 出参：无

subscribe()函数用于订阅行情信息，若需要订阅一篮子合约的行情，可以使用列表格式。
```python 3
engine.subscribe(vt_symbols = ["rb2209.SHFE","rb2210.SHFE"])
```

### 查询数据
这里介绍一下连接上交易接口并成功订阅数据后的数据存储：

- 底层接口不停向主引擎推送新的数据；
- 主引擎里维护着一个ticks字典用于缓存不同标的的最新tick数据（仅能缓存最新数据）；
- use_df的作用是转换成DataFrame格式，便于数据分析。

#### 单条查询

**get_tick**

* 入参：vt_symbol: str, use_df: bool = False

* 出参：TickData

查询单个标的最新tick，use_df为可选参数，用于把返回的类对象转化成DataFrame格式，便于数据分析。

```python 3
tick = engine.get_tick(vt_symbol="rb2210.SHFE",use_df=False)
```

其中：

- vt_symbol：为本地合约代码，格式是合约品种+交易所，如rb2210.SHFE；
- use_df：为bool变量，默认False，返回TickData类对象，否则返回相应DataFrame，如下图所示：

![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/13.png)

**get_order**

* 入参：vt_orderid: str, use_df: bool = False

* 出参：OrderData

根据vt_orderid查询委托单的详细信息。

```python 3
order = engine.get_order(vt_orderid="CTP.3_-1795780178_1",use_df=False)
```

其中，vt_orderid为本地委托号（在委托下单时，会自动返回该委托的vt_orderid）。
![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/14.png)

**get_contract**

* 入参：vt_symbol, use_df: bool = False

* 出参：ContractData

根据本地vt_symbol来查询对应合约对象的详细信息。

```python 3
contract = engine.get_contract(vt_symbol="rb2210.SHFE",use_df=False)
```
![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/15.png)

**get_account**

* 入参：vt_accountid: str, use_df: bool = False

* 出参：AccountData

根据本地vt_accountid来查询对应资金信息。

```python 3
account = engine.get_account(vt_accountid="CTP.189672",use_df=False)
```
![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/16.png)

**get_position**

* 入参：vt_positionid: str, use_df: bool = False

* 出参：PositionData

根据vt_positionid来查询持仓情况，返回对象包含接口名称、交易所、合约代码、数量、冻结数量等。

```python 3
position = engine.get_position(vt_positionid='rb2202.SHFE.多')
```
注意，vt_positionid为vnpy内部对于一笔特定持仓的唯一持仓编号，格式为"vt_symbol.Direction.value"，其中持仓方向可选“多”、“空”和“净”，如下图所示：
![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/17.png)

#### 多条查询

**get_ticks**

* 入参：vt_symbols: Sequence[str], use_df: bool = False

* 出参：Sequence[TickData]

查询多个合约最新tick。

```python 3
ticks = engine.get_ticks(vt_symbols=['rb2209.SHFE','rb2210.SHFE'],use_df=True)
```

vt_symbols是列表格式，里面包含多个vt_symbol，如图。
![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/18.png)


**get_orders**

* 入参：vt_orderids: Sequence[str], use_df: bool = False

* 出参：Sequence[OrderData]

根据查询多个vt_orderid查询其详细信息。vt_orderids为列表，里面包含多个vt_orderid。

```python 3
orders = engine.get_orders([orderid_one,orderid_two],use_df=True)
```

**get_trades**

* 入参：vt_orderid: str, use_df: bool = False

* 出参：Sequence[TradeData]

根据给定的一个vt_orderid返回这次报单过程中的所有TradeData对象。vt_orderid是本地委托号，每一个委托OrderData，由于部分成交关系，可以对应多笔成交TradeData。

```python 3
trades = engine.get_trades(vt_orderid=your_vt_orderid,use_df=True)
```

**get_bars**

* 入参：vt_symbol: str, start_date: str, interval: Interval, use_df: bool = False

* 出参：Sequence[BarData]

通过配置的数据服务查询历史数据。

```python 3
bars = engine.get_bars(vt_symbol="rb2210.SHFE",start_date="20211201",
                        interval=Interval.MINUTE,use_df=False)
```

其中：

- vt_symbol：本地合约代码，格式为合约代码 + 交易所名称；
- start_date：起始日期，格式为"%Y%m%d"；
- interval：K线周期，包括：分钟、小时、日、周；
- bars：包含了一系列BarData数据的列表对象，其BarData的定义如下：
```python 3
@dataclass
class BarData(BaseData):

    symbol: str
    exchange: Exchange
    datetime: datetime

    interval: Interval = None
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    open_price: float = 0
    high_price: float = 0
    low_price: float = 0
    close_price: float = 0

    def __post_init__(self):
        self.vt_symbol = f"{self.symbol}.{self.exchange.value}"
```

#### 全量查询

在全量查询中，唯一参数是use_df，默认为False。返回的是一个包含相应数据的List对象，例如ContractData、AccountData和PositionData。

**get_all_contracts**

* 入参：use_df: bool = False

* 出参：Sequence[ContractData]

默认返回一个list，包含了全市场的ContractData，如果use_df=True则返回相应的DataFrame。

**get_all_active_orders**

* 入参：use_df: bool = False

* 出参：Sequence[OrderData]

活动委托指的是等待委托完全成交，故其状态包含“已提交、未成交、部分成交”；函数将返回包含一系列OrderData的列表对象。

**get_all_accounts**

* 入参：use_df: bool = False

* 出参：Sequence[AccountData]

默认返回包含AccountData的列表对象。

**get_all_positions**

* 入参：use_df: bool = False

* 出参：Sequence[PositionData]

默认返回包含PositionData的列表对象，如下图所示：
![](https://vnpy-doc.oss-cn-shanghai.aliyuncs.com/script_trader/19.png)

### 交易委托

**buy**：买入开仓（Direction：LONG，Offset：OPEN）

**sell**：卖出平仓（Direction：SHORT，Offset：CLOSE）

**short**：卖出开仓（Direction：SHORT，Offset：OPEN）

**cover**：买入平仓（Direction：LONG，Offset：CLOSE）

* 入参：vt_symbol: str, price: float, volume: float, order_type: OrderType = OrderType.LIMIT

* 出参：str

以委托买入为例，engine.buy()函数入参包括：

- vt_symbol：本地合约代码（字符串格式）；
- price：报单价格（浮点数类型）;
- volume：报单数量（浮点数类型）;
- order_type：OrderType枚举常量，默认为限价单（OrderType.LIMIT），同时支持停止单（OrderType.STOP）、FAK（OrderType.FAK）、FOK（OrderType.FOK）、市价单（OrderType.MARKET），不同交易所支持报单方式不完全一致。
```python 3
engine.buy(vt_symbol="rb2210.SHFE", price=4200, volume=1, order_type=OrderType.LIMIT)
```

执行交易委托后会返回本地委托号vt_orderid。

**send_order**

* 入参：vt_symbol: str, price: float, volume: float, direction: Direction, offset: Offset, order_type: OrderType

* 出参：str

send_order函数是脚本交易策略引擎调用的发送委托的函数。一般在策略编写的时候不需要单独调用，通过buy/sell/short/cover函数发送委托即可。

**cancel_order**

* 入参：vt_orderid: str

* 出参：无 

基于本地委托号撤销委托。

```python 3
engine.cancel_order(vt_orderid='CTP.3_-1795780178_1')
```

### 信息输出

**write_log**

* 入参：msg: str

* 出参：无

在策略中调用write_log函数，可以进行指定内容的日志输出。

**send_email**

* 入参：msg: str

* 出参：无

配置好邮箱相关信息之后（配置方法详见基本使用篇的全局配置部分），调用send_email函数可以发送标题为“脚本策略引擎通知”的邮件到自己的邮箱。
