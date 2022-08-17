import zmq
import json
import re
import threading

class TCoreZMQ():
    def __init__(self,APPID,SKey):
        self.context = zmq.Context()
        self.appid=APPID
        self.ServiceKey=SKey
        self.lock = threading.Lock()
        self.m_objZMQKeepAlive = None

    #連線登入
    def Connect(self, port):
        for i in range(1000):
            result = self.ConnectSystem(int(port)+i, 100)
            ret = result["Success"]
            if ret != "ConnectError":
                break
        return result
        
    def ConnectSystem(self, port, timeout):
        self.lock.acquire()
        login_obj = {"Request":"LOGIN","Param":{"SystemName":self.appid, "ServiceKey":self.ServiceKey}}
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.RCVTIMEO, timeout)
        self.socket.connect("tcp://127.0.0.1:%d" % port)
        self.socket.send_string(json.dumps(login_obj))
        try:
            message = self.socket.recv()
            message = message[:-1]
            data = json.loads(message)
            if data["Success"] == "OK":
                self.socket.close()
                self.socket = self.context.socket(zmq.REQ)
                self.socket.connect("tcp://127.0.0.1:%d" % port)
                self.LoginOK = True
                self.lock.release()
                self.CreatePingPong(data["SessionKey"], data["SubPort"])
        except:
            self.socket.close()
            self.lock.release()
            data = json.loads("{\"Success\":\"ConnectError\"}")

        return data

    def CreatePingPong(self, sessionKey, subPort):
        if self.m_objZMQKeepAlive != None:
            self.m_objZMQKeepAlive.Close()
        
        self.m_objZMQKeepAlive = KeepAliveHelper(subPort, sessionKey, self)
        
        return

    #連線登出
    def Logout(self, sessionKey):
        self.m_objZMQKeepAlive.Close()
        self.lock.acquire()
        obj = {"Request":"LOGOUT","SessionKey":sessionKey}
        self.socket.send_string(json.dumps(obj))
        self.lock.release()
        return

    #查詢合約信息
    def QueryInstrumentInfo(self, sessionKey, symbol):
        self.lock.acquire()
        obj = {"Request" : "QUERYINSTRUMENTINFO" , "SessionKey" : sessionKey , "Symbol" : symbol}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #查詢對應類型的所有合約
    #"Type":
    #期貨：Future
    #期權：Options
    #證券：Stock
    def QueryAllInstrumentInfo(self, sessionKey, type):
        self.lock.acquire()
        obj = {"Request": "QUERYALLINSTRUMENT", "SessionKey": sessionKey, "Type": type}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #連線心跳（在收到"PING"消息時調用）
    def Pong(self, sessionKey, id = ""):
        self.lock.acquire()
        obj = {"Request":"PONG","SessionKey":sessionKey, "ID":id}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

class TradeAPI(TCoreZMQ):
    def __init__(self,APPID, SKey):
        super().__init__(APPID, SKey)

    #已登入資金賬戶
    def QryAccount(self, sessionKey):
        self.lock.acquire()
        obj = {"Request":"ACCOUNTS","SessionKey":sessionKey}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #查詢當日委托回報
    def QryReport(self, sessionKey, qryIndex):
        self.lock.acquire()
        obj = {"Request":"RESTOREREPORT","SessionKey":sessionKey,"QryIndex":qryIndex}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #查詢當日成交回報
    def QryFillReport(self, sessionKey, qryIndex):
        self.lock.acquire()
        obj = {"Request":"RESTOREFILLREPORT","SessionKey":sessionKey,"QryIndex":qryIndex}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #下單
    def NewOrder(self, sessionKey, param):
        self.lock.acquire()
        obj = {"Request":"NEWORDER","SessionKey":sessionKey}
        obj["Param"] = param
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #改單
    def ReplaceOrder(self, sessionKey, param):
        self.lock.acquire()
        obj = {"Request":"REPLACEORDER","SessionKey":sessionKey}
        obj["Param"] = param
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #刪單
    def CancelOrder(self, sessionKey, param):
        self.lock.acquire()
        obj = {"Request":"CANCELORDER","SessionKey":sessionKey}
        obj["Param"] = param
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data
        
    #查詢資金
    def QryMargin(self, sessionKey, accountMask):
        self.lock.acquire()
        obj = {"Request":"MARGINS","SessionKey":sessionKey,"AccountMask":accountMask}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #查詢持倉
    def QryPosition(self, sessionKey, accountMask, qryIndex):
        self.lock.acquire()
        obj = {"Request":"POSITIONS","SessionKey":sessionKey,"AccountMask":accountMask,"QryIndex":qryIndex}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    def QryOptCombOrder(self, key, AM, qryIndex):
        self.lock.acquire()
        obj = {"Request":"QUERYOPTCOMBORDER","SessionKey":key,"AccountMask":AM,"QryIndex":qryIndex}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    def OptComb(self, key, Param):
        self.lock.acquire()
        obj = {"Request":"OPTCOMB","SessionKey":key}
        obj["Param"] = Param
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data
    #查詢持倉監控
    def QryPositionTracker(self, sessionKey):
        self.lock.acquire()
        obj = {"Request":"POSITIONTRACKER","SessionKey":sessionKey}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data
        
class QuoteAPI(TCoreZMQ):
    def __init__(self,APPID, SKey):
        super().__init__(APPID, SKey)

    #訂閱實時報價
    def SubQuote(self, sessionKey, symbol):
        self.lock.acquire()
        obj = {"Request":"SUBQUOTE","SessionKey":sessionKey}
        obj["Param"] ={"Symbol":symbol,"SubDataType":"REALTIME"}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #解訂實時報價(每次訂閱合約前，先調用解訂，避免重覆訂閱)
    def UnsubQuote(self, sessionKey, symbol):
        self.lock.acquire()
        obj = {"Request":"UNSUBQUOTE","SessionKey":sessionKey}
        obj["Param"] = {"Symbol":symbol,"SubDataType":"REALTIME"}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #訂閱實時greeks
    def SubGreeks(self, sessionKey, symbol, greeksType = "REAL"):
        self.lock.acquire()
        obj = {"Request":"SUBQUOTE","SessionKey":sessionKey}
        obj["Param"] = {"Symbol":symbol,"SubDataType":"GREEKS","GreeksType":greeksType}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #解訂實時greeks(每次訂閱合約前，先調用解訂，避免重覆訂閱)
    def UnsubGreeks(self, sessionKey, symbol, greeksType = "REAL"):
        self.lock.acquire()
        obj = {"Request":"UNSUBQUOTE","SessionKey":sessionKey}
        obj["Param"] = {"Symbol":symbol,"SubDataType":"GREEKS","GreeksType":greeksType}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #訂閱歷史數據    
    #1：SessionKey，
    #2：合約代碼，
    #3：數據周期:"TICKS","1K","DK"，
    #4: 歷史數據開始時間,
    #5: 歷史數據結束時間
    def SubHistory(self, sessionKey, symbol, type, startTime, endTime):
        self.lock.acquire()
        obj = {"Request":"SUBQUOTE","SessionKey":sessionKey}
        obj["Param"] = {"Symbol": symbol,"SubDataType":type,"StartTime" :startTime,"EndTime" :endTime}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data 

    #解訂歷史數據（遺棄，不再使用）
    #1：SessionKey，
    #2：合約代碼，
    #3：數據周期"TICKS","1K","DK"，
    #4: 歷史數據開始時間,
    #5: 歷史數據結束時間   
    def UnsubHistory(self, sessionKey, symbol, type, startTime, endTime):
        self.lock.acquire()
        obj = {"Request":"UNSUBQUOTE","SessionKey":sessionKey}
        obj["Param"] = {"Symbol": symbol,"SubDataType":type,"StartTime" :startTime,"EndTime" :endTime}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #分頁獲取訂閱的歷史數據
    def GetHistory(self, sessionKey, symbol, type, startTime, endTime, qryIndex):
        self.lock.acquire()
        obj = {"Request":"GETHISDATA","SessionKey":sessionKey}
        obj["Param"] = {"Symbol": symbol,"SubDataType":type,"StartTime" :startTime,"EndTime" :endTime,"QryIndex" :qryIndex}
        self.socket.send_string(json.dumps(obj))
        message = (self.socket.recv()[:-1]).decode("utf-8")
        index =  re.search(":",message).span()[1]  # filter
        message = message[index:]
        message = json.loads(message)
        self.lock.release()
        return message

    def GetHotChange(self, sessionKey, symbol, startTime, endTime):
        self.lock.acquire()
        obj = {"Request":"GETHOTCHANGE","SessionKey":sessionKey}
        obj["Param"] = {"Symbol": symbol,"StartTime" :startTime,"EndTime" :endTime}
        self.socket.send_string(json.dumps(obj))
        message = self.socket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

class KeepAliveHelper():
    def __init__(self, subPort, session, objZMQ):
        threading.Thread(target = self.ThreadProcess, args=(subPort, session, objZMQ)).start()
        self.IsTerminal = False

    def Close(self):
        self.IsTerminal = True

    def ThreadProcess(self, subPort, session, objZMQ):
        socket_sub = zmq.Context().socket(zmq.SUB)
        socket_sub.connect("tcp://127.0.0.1:%s" % subPort)
        socket_sub.setsockopt_string(zmq.SUBSCRIBE,"")
        while True:
            message = (socket_sub.recv()[:-1]).decode("utf-8")
            findText = re.search("{\"DataType\":\"PING\"}",message)

            if findText == None:
                continue

            if self.IsTerminal:
                return

            objZMQ.Pong(session, "TC")