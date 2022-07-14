import time
import json
import re
import pandas as pd
import zmq

g_DictHistory = {}

#實時行情Callback
#相關欄位，參考本範例欄位注解
def OnRealTimeQuote(symbol):
    print("FilledTime > ", symbol["FilledTime"], " > Symbol: ",symbol["Symbol"] , " > TradingPrice:", symbol["TradingPrice"])
    # print("O: ",symbol["OpeningPrice"])
    # print("H: ",symbol["HighPrice"])
    # print("L: ",symbol["LowPrice"])
    # print("C: ",symbol["ClosingPrice"])

#實時GreeksCallback
def OnGreeks(greek):
    print(
        "TradingHours:", greek["TradingHours"], 
        "ImpVol > ", greek["ImpVol"],
        "BIV > ", greek["BIV"],
        "SIV > ", greek["SIV"],
        "Delta > ", greek["Delta"],
        "Gamma > ", greek["Gamma"],
        "Vega > ", greek["Vega"],
        "Theta > ", greek["Theta"],
        "Rho > ", greek["Rho"],
        "TheoVal > ", greek["TheoVal"],
        "ExtVal > ", greek["ExtVal"]
    )

def GetHistory(g_QuoteZMQ, g_QuoteSession , symbol, type, startTime, endTime):
    HisKey = symbol + "-" + type + "-" + startTime + "-" + endTime
    g_QuoteZMQ.SubHistory(g_QuoteSession, symbol, type, startTime, endTime)

    timeout = 10    
    mustend = time.time() + timeout
    while time.time() < mustend:
        if HisKey in g_DictHistory.keys(): 
            break
        time.sleep(0.5)

    dataAll = []
    strQryIndex = ""
    while(True):
        if not HisKey in g_DictHistory.keys():
            break;

        s_history = g_QuoteZMQ.GetHistory(g_QuoteSession, symbol, type, startTime, endTime, strQryIndex)
        historyData = s_history["HisData"]
        if len(historyData) == 0:
            break

        last = historyData[-1]
        
        for data in historyData:
            dataAll.append(data)
        
        strQryIndex = last["QryIndex"]

    g_QuoteZMQ.UnsubHistory(g_QuoteSession, symbol, type, startTime, endTime)
    g_DictHistory.pop(HisKey, None)

    dfAll = pd.read_json(json.dumps(dataAll))
    print(dfAll)
    return dfAll

#行情消息接收
def quote_sub_th(obj,sub_port,filter = ""):
    socket_sub = obj.context.socket(zmq.SUB)
    #socket_sub.RCVTIMEO=7000   #ZMQ超時時間設定
    socket_sub.connect("tcp://127.0.0.1:%s" % sub_port)
    socket_sub.setsockopt_string(zmq.SUBSCRIBE,filter)
    while(True):
        message = (socket_sub.recv()[:-1]).decode("utf-8")
        index =  re.search(":",message).span()[1]  # filter
        message = message[index:]
        message = json.loads(message)
        #for message in messages:
        if(message["DataType"]=="REALTIME"):
            OnRealTimeQuote(message["Quote"])
        elif(message["DataType"]=="GREEKS"):
            OnGreeks(message["Quote"])
        elif(message["DataType"]=="DOGSK"  or message["DataType"]=="DOGSS" or message["DataType"]=="TICKS" or message["DataType"]=="1K" or message["DataType"]=="DK"):
            print(message["DataType"])
            HisKey = message["Symbol"] + "-" + message["DataType"] + "-" + message["StartTime"] + "-" + message["EndTime"]
            g_DictHistory[HisKey] = HisKey            
    return