import time
import json
import re
import zmq

#已登入資金賬戶變更
def OnGetAccount( account ):
    print(account["BrokerID"])

#實時委托回報消息
def OnexeReport( report ):
    global ReportID
    # print( report )
    print("RealTimeReport>", report["ReportID"], "OrerID > " , report["OrderID"])
    return None

#實時成交回報回調
def RtnFillReport( report ):
    print("RtnFillReport:", report["ReportID"])

#查詢當日歷史委托回報回調
def ShowEXECUTIONREPORT(g_TradeZMQ, SessionKey, reportData):
    if reportData["Reply"] == "RESTOREREPORT":
        Orders = reportData["Orders"]
        if len(Orders) == 0:
            return
        last = ""
        for data in Orders:
            last = data
            print( "Report:", data['ReportID'] )
        reportData = g_TradeZMQ.QryReport(SessionKey,last["QryIndex"])
        ShowEXECUTIONREPORT(g_TradeZMQ,SessionKey,reportData)

#查詢當日歷史委托成交回調
def ShowFillReport(g_TradeZMQ, SessionKey, reportData):
    if reportData["Reply"] == "RESTOREFILLREPORT":
        Orders = reportData["Orders"]
        if len(Orders) == 0:
            return

        last = ""
        for data in Orders:
            last = data
            print( "Filled:", data['ReportID'] )

        reportData = g_TradeZMQ.QryFillReport(SessionKey,last["QryIndex"])
        ShowFillReport(g_TradeZMQ,SessionKey,reportData)

#查詢持倉消息回調
def ShowPOSITIONS( g_TradeZMQ, SessionKey, AccountMask, positionData ):
    if positionData["Reply"] == "POSITIONS":
        position = positionData["Positions"]
        if len(position) == 0:
            return

        last = ""
        for data in position:
            last = data
            print("Position:", data["Symbol"])

        positionData = g_TradeZMQ.QryPosition(SessionKey,AccountMask,last["QryIndex"])
        ShowPOSITIONS(g_TradeZMQ,SessionKey,AccountMask,positionData)
#查詢持倉監控
def QryPositionTracker( g_TradeZMQ, g_TradeSession):
    data = g_TradeZMQ.QryPositionTracker(g_TradeSession)
    print("QryPositionTracker:", data)

#交易消息接收
def trade_sub_th(obj,sub_port,filter = ""):
    socket_sub = obj.context.socket(zmq.SUB)
    #socket_sub.RCVTIMEO=5000           #ZMQ超時時間設定
    socket_sub.connect("tcp://127.0.0.1:%s" % sub_port)
    socket_sub.setsockopt_string(zmq.SUBSCRIBE,filter)
    while True:
        message =  socket_sub.recv()
        if message:
            message = json.loads(message[:-1])
            #print("in trade message",message)
            if(message["DataType"] == "ACCOUNTS"):
                for i in message["Accounts"]:
                    OnGetAccount(i)
            elif(message["DataType"] == "EXECUTIONREPORT"):
                OnexeReport(message["Report"])
            elif(message["DataType"] == "FILLEDREPORT"):
                RtnFillReport(message["Report"])
            elif(message["DataType"] == "POSITIONTRACKER"):
                QryPositionTracker()