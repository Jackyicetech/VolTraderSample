import zmq
import json
import threading
import re
from queue import Queue,Empty
import logging
import time
import uuid
from datetime import datetime, timedelta
import pytz
#import pdb


class TradeClass():
    def __init__(self):
        self.context = zmq.Context()
        self.lock = threading.Lock()
        self.tsocket=None
        self.tsessionKey=""
        self.teventQueue=Queue()
        self.LoginOK=False
        self.m_objZMQKeepAlive = None
        self.orderinfo={}
    def tdupdate(self):
        try:
            return self.teventQueue.get_nowait()#(block=True, timeout=None)
        except Empty:
            return
    def trade_connect(self,appid,ServiceKey,port):
        self.lock.acquire()
        login_obj = {"Request":"LOGIN","Param":{"SystemName":appid, "ServiceKey":ServiceKey}}
        self.tsocket = self.context.socket(zmq.REQ)
        self.tsocket.connect("tcp://127.0.0.1:%s" % port)
        self.tsocket.send_string(json.dumps(login_obj))
        message = self.tsocket.recv()
        message = message[:-1]
        data = json.loads(message)
        self.lock.release()
        if data["Success"] == "OK":
            self.LoginOK = True
            self.tsessionKey=data["SessionKey"]
            threading.Thread(target = self.trade_sub_th,args=(data["SubPort"],"")).start()
            self.CreatePingPong(data,self.tsocket)
            return "OK"
        else:
            print("交易连线失败")
            return

    #连线登出
    def trade_logout(self):
        self.LoginOK = False
        self.lock.acquire()
        obj = {"Request":"LOGOUT","SessionKey":self.tsessionKey}
        self.tsocket.send_string(json.dumps(obj))
        self.lock.release()
        return

    #已登入资金账户
    def QryAccount(self):
        self.lock.acquire()
        obj = {"Request":"ACCOUNTS","SessionKey":self.tsessionKey}
        self.tsocket.send_string(json.dumps(obj))
        message = self.tsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #查询当日委托回报
    def QryReport(self):
        datas=[]
        last=""
        while True:
            self.lock.acquire()
            obj = {"Request":"RESTOREREPORT","SessionKey":self.tsessionKey,"QryIndex":last}
            self.tsocket.send_string(json.dumps(obj))
            message = self.tsocket.recv()[:-1]
            data = json.loads(message)
            self.lock.release()
            if data["Reply"] == "RESTOREREPORT":
                if len(data["Orders"]) == 0:
                    break
                for ord in data["Orders"]:
                    datas.append(ord)
                    last = ord["QryIndex"]
            return datas

    #查询当日成交回报
    def QryFillReport(self):
        datas=[]
        last=""
        while True:
            self.lock.acquire()
            obj = {"Request":"RESTOREFILLREPORT","SessionKey":self.tsessionKey,"QryIndex":last}
            self.tsocket.send_string(json.dumps(obj))
            message = self.tsocket.recv()[:-1]
            data = json.loads(message)
            self.lock.release()
            if data["Reply"] == "RESTOREFILLREPORT":
                if len(data["Orders"]) == 0:
                    break
                for ord in data["Orders"]:
                    datas.append(ord)
                    last = ord["QryIndex"]
            return datas
    
    #获取委托单信息
    def getorderinfo(self, ordid):
        if ordid in self.orderinfo.keys():
            return self.orderinfo[ordid]
        else:
            return
    #下单
    def NewOrder(self, param):
        self.lock.acquire()
        obj = {"Request":"NEWORDER","SessionKey":self.tsessionKey}
        param["UserKey1"]=str(uuid.uuid1())
        param["UserKey2"]=self.tsessionKey
        obj["Param"] = param
        self.tsocket.send_string(json.dumps(obj))
        message = self.tsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        if data['Success']=='OK':
            return param["UserKey1"]
        elif data['ErrCode']=="-10":
            print("unknow error")
            return
        elif data['ErrCode']=="-11":
            print("买卖别错误")
            return
        elif data['ErrCode']=="-12":
            print("复式单商品代码解晰错误 ")
            return
        elif data['ErrCode']=="-13":
            print("下单账号, 不可下此交易所商品")
            return
        elif data['ErrCode']=="-14":
            print("下单错误, 不支持的价格 或 OrderType 或 TimeInForce ")
            return
        elif data['ErrCode']=="-15":
            print("不支援证券下单")
            return
        elif data['ErrCode']=="-20":
            print("联机未建立")
            return
        elif data['ErrCode']=="-22":
            print("价格的 TickSize 错误")
            return
        elif data['ErrCode']=="-23":
            print("下单数量超过该商品的上下限 ")
            return
        elif data['ErrCode']=="-24":
            print("下单数量错误 ")
            return
        elif data['ErrCode']=="-25":
            print("价格不能小于和等于 0 (市价类型不会去检查) ")
            return
    #策略单
    def NewStrategyOrder(self, param):
        self.lock.acquire()
        obj = {"Request":"NEWSTRATEGYORDER","SessionKey":self.tsessionKey}
        obj["Param"] = param
        self.tsocket.send_string(json.dumps(obj))
        message = self.tsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #改单
    def ReplaceOrder(self, param):
        self.lock.acquire()
        obj = {"Request":"REPLACEORDER","SessionKey":self.tsessionKey}
        obj["Param"] = param
        self.tsocket.send_string(json.dumps(obj))
        message = self.tsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        if data['Success']=='OK':
            return data 
        else:
            print("改单错误：",data['ErrCode'])

    #删单
    def CancelOrder(self, param):
        self.lock.acquire()
        obj = {"Request":"CANCELORDER","SessionKey":self.tsessionKey}
        obj["Param"] = param
        self.tsocket.send_string(json.dumps(obj))
        message = self.tsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data
        
    #查询资金
    def QryMargin(self, accountMask):
        self.lock.acquire()
        obj = {"Request":"MARGINS","SessionKey":self.tsessionKey,"AccountMask":accountMask}
        self.tsocket.send_string(json.dumps(obj))
        message = self.tsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #查询持仓
    def QryPosition(self,accountMask):
        datas=[]
        last=""
        while True:
            self.lock.acquire()
            obj = {"Request":"POSITIONS","SessionKey":self.tsessionKey,"AccountMask":accountMask,"QryIndex":last}
            self.tsocket.send_string(json.dumps(obj))
            message = self.tsocket.recv()[:-1]
            data = json.loads(message)
            self.lock.release()
            if data["Reply"] == "POSITIONS":
                if len(data["Positions"]) == 0:
                    break
                for ord in data["Positions"]:
                    datas.append(ord)
                    last = ord["QryIndex"]
            return datas
    #查询新建组合的委托回报
    def QryOptCombOrder(self, AM, qryIndex=""):
        datas=[]
        last=""
        while True:
            self.lock.acquire()
            obj = {"Request":"QUERYOPTCOMBORDER","SessionKey":self.tsessionKey,"AccountMask":AM,"QryIndex":last}
            self.tsocket.send_string(json.dumps(obj))
            message = self.tsocket.recv()[:-1]
            data = json.loads(message)
            self.lock.release()
            if data["Reply"] == "QUERYOPTCOMBORDER":
                if len(data['Orders']) == 0:
                    break
                for ord in data['Orders']:
                    datas.append(ord)
                    last = ord["QryIndex"]
            return datas
    #建组合
    def OptComb(self, Param):
        self.lock.acquire()
        obj = {"Request":"OPTCOMB","SessionKey":self.tsessionKey}
        obj["Param"] = Param
        self.tsocket.send_string(json.dumps(obj))
        message = self.tsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data
    #查询组合持仓
    def QryOptCombPosition(self,accountMask, qryIndex=""):
        datas=[]
        last=""
        while True:
            self.lock.acquire()
            obj = {"Request":"QUERYOPTCOMBPOSITION","SessionKey":self.tsessionKey,"AccountMask":accountMask,"QryIndex":last}
            self.tsocket.send_string(json.dumps(obj))
            message = self.tsocket.recv()[:-1]
            data = json.loads(message)
            self.lock.release()
            if data["Reply"] == "QUERYOPTCOMBPOSITION":
                if len(data["Positions"]) == 0:
                    break
                for ord in data["Positions"]:
                    datas.append(ord)
                    last = ord["QryIndex"]
            return datas


    #查询持仓监控
    def QryPositionTracker(self):
        self.lock.acquire()
        obj = {"Request":"POSITIONTRACKER","SessionKey":self.tsessionKey}
        self.tsocket.send_string(json.dumps(obj))
        message = self.tsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    def CreatePingPong(self, sessiondata,stkobj):
        #if self.m_objZMQKeepAlive != None:
        #    self.m_objZMQKeepAlive.Close()
        self.m_objZMQKeepAlive = KeepAliveHelper(sessiondata,self,stkobj)
        
        return

    def trade_sub_th(self,port,filter = ""):
        socket_sub = self.context.socket(zmq.SUB)
        #socket_sub.RCVTIMEO=5000
        socket_sub.connect("tcp://127.0.0.1:%s" % port)
        socket_sub.setsockopt_string(zmq.SUBSCRIBE,filter)
        messagetemp=""
        while threading.main_thread().is_alive():
            message =  socket_sub.recv()
            if message:
                message = json.loads(message[:-1])
                if message['DataType']== 'EXECUTIONREPORT' and messagetemp!=message:
                    self.teventQueue.put(message)
                    if message["Report"]["UserKey2"]==self.tsessionKey:
                        self.orderinfo[message["Report"]["UserKey1"]]=message["Report"] 
                elif message['DataType']!= 'PING':
                    self.teventQueue.put(message)
                messagetemp=message

class QuoteClass():
    def __init__(self):
        self.context = zmq.Context()
        self.lock = threading.Lock()
        self.qsocket=None
        self.qsessionKey=""

        self.eventQueue=Queue()
        self.lasthistorydata={}
        self.m_objZMQKeepAlive = None
        self.LoginOK = False
        self.realdate={}
        self.status=[]

        self.gmt = pytz.timezone('Etc/GMT')

    #def __del__(self):
    #    self.quote_logout()

    def mdupdate(self):
        #return self.eventQueue.get(block=True, timeout=None)
        try:
            return self.eventQueue.get_nowait()#(block=True, timeout=None)
        except Empty:
            return

    #建立行情连线
    def quote_connect(self,appid,ServiceKey, port):
        self.lock.acquire()
        login_obj = {"Request":"LOGIN","Param":{"SystemName":appid, "ServiceKey":ServiceKey}}
        self.qsocket = self.context.socket(zmq.REQ)
        self.qsocket.connect("tcp://127.0.0.1:%s" % port)
        self.qsocket.send_string(json.dumps(login_obj))
        message = self.qsocket.recv()
        message = message[:-1]
        data = json.loads(message)
        self.lock.release()
        if data["Success"] == "OK":
            self.LoginOK = True
            self.qsessionKey=data["SessionKey"]
            threading.Thread(target = self.quote_sub_th,args=(data["SubPort"],"")).start()
            self.CreatePingPong(data,self.qsocket)
            return "OK"
        else:
            print("行情连线失败")
            return

    #连线登出
    def quote_logout(self):
        self.LoginOK = False
        self.lock.acquire()
        obj = {"Request":"LOGOUT","SessionKey":self.qsessionKey}
        self.qsocket.send_string(json.dumps(obj))
        self.lock.release()
        return

    #订阅实时报价
    def SubQuote(self,symbol):

        result=[]
        if not isinstance(symbol, list):
            symbol=[symbol]
        for sym in symbol:
            self.lock.acquire()
            obj = {"Request":"SUBQUOTE","SessionKey":self.qsessionKey}
            obj["Param"] ={"Symbol":sym,"SubDataType":"REALTIME"}
            self.qsocket.send_string(json.dumps(obj))
            message = self.qsocket.recv()[:-1]
            data = json.loads(message)
            self.lock.release()
            data['symbol']=sym
            result.append(data)
        return result

    #解订实时报价
    def UnsubQuote(self,symbol):
        result=[]
        if not isinstance(symbol, list):
            symbol=[symbol]
        for sym in symbol:
            self.lock.acquire()
            obj = {"Request":"UNSUBQUOTE","SessionKey":self.qsessionKey}
            obj["Param"] = {"Symbol":sym,"SubDataType":"REALTIME"}
            self.qsocket.send_string(json.dumps(obj))
            message = self.qsocket.recv()[:-1]
            data = json.loads(message)
            self.lock.release()
            data['symbol']=sym
            result.append(data)
        return result

    #订阅实时greeks
    def SubGreeks(self,symbol, greeksType = "REAL"):
        result=[]
        if not isinstance(symbol, list):
            symbol=[symbol]
        for sym in symbol:
            self.lock.acquire()
            if "TC.F.U_" in sym:
                greeksType = "Volatility"
            else:
                greeksType = "REAL"
            obj = {"Request":"SUBQUOTE","SessionKey":self.qsessionKey}
            obj["Param"] = {"Symbol":sym,"SubDataType":"GREEKS","GreeksType":greeksType}
            self.qsocket.send_string(json.dumps(obj))
            message = self.qsocket.recv()[:-1]
            data = json.loads(message)
            self.lock.release()
            data['symbol']=sym
            result.append(data)
        return result

    #解订实时greeks
    def UnsubGreeks(self, symbol, greeksType = "REAL"):
        result=[]
        if not isinstance(symbol, list):
            symbol=[symbol]
        for sym in symbol:
            self.lock.acquire()
            if "TC.F.U_" in sym:
                greeksType = "Volatility"
            else:
                greeksType = "REAL"
            obj = {"Request":"UNSUBQUOTE","SessionKey":self.qsessionKey}
            obj["Param"] = {"Symbol":symbol,"SubDataType":"GREEKS","GreeksType":greeksType}
            self.qsocket.send_string(json.dumps(obj))
            message = self.qsocket.recv()[:-1]
            data = json.loads(message)
            self.lock.release()
            data['symbol']=sym
            result.append(data)
        return result

    #订阅历史数据    
    #1：SessionKey，
    #2：合约代码，
    #3：数据周期:
        # tick: "TICKS",
        # 分K: "1K",
        # 日K: "DK"，
        # DOGS秒："DOGSS",
        # DOGS分K："DOGSK"
    #4: 历史数据开始时间,
    #5: 历史数据结束时间
    def SubHistory(self,symbol, bartype, startTime, endTime,dbtype=""):
        if not (re.match("TC.S.", symbol) or re.match("TC.F.", symbol) or re.match("TC.O.", symbol) or\
        re.match("TC.SP.", symbol) or re.match("TC.F2.", symbol) or re.match("TC.O2.", symbol)):
            print("合约代码格式错误")
            return        
        if bartype=="3K" or bartype=="5K" or bartype=="15K":
            m_type="1K"
        else:
            m_type=bartype

        if symbol+bartype not in self.lasthistorydata.keys():#and int(int(endTime)/100)>=int(time.strftime("%Y%m%d",time.localtime())):
            self.lasthistorydata[symbol+bartype]= {"Symbol": symbol,"DataType":bartype,"StartTime" :startTime,"EndTime" :endTime,"lastindex":""}
        self.lock.acquire()
        obj = {"Request":"SUBQUOTE","SessionKey":self.qsessionKey}
        obj["Param"] = {"Symbol": symbol,"SubDataType":m_type,"StartTime" :startTime,"EndTime" :endTime}

        self.qsocket.send_string(json.dumps(obj))
        message = self.qsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        

        if data['Success']=='OK':
            while True:
                if self.getstatus(symbol, bartype, startTime, endTime,dbtype)=='Ready':
                    temp=[]
                    last=""
                    if dbtype=="ODBC":
                        if bartype=="DOGSK" or bartype=="DOGSS":
                            temp.append('Ready')
                            return temp
                        else:
                            print("只有DOGSK和DOGSS周期支持ODBC")
                            return None
                    #his=self.gethistory(symbol, type, startTime, endTime)

                    while True:
                        his=self.__get_history(symbol, bartype, startTime, endTime,last)
                        
                        if his and len(his["HisData"])>0:
                            for his1 in his["HisData"]:
                                last=his1['QryIndex']
                                temphis={"Symbol":symbol}
                                if bartype=="DOGSK" or bartype=="DOGSS":
                                    t=str(int(int(his1['t'])/1000))
                                    temphis["DateTime"]=datetime.strptime(his1['d']+(" 0" if len(t)==5 else " ")+t,"%Y%m%d %H%M%S").replace(tzinfo=self.gmt)
                                    #del his1["d"]
                                    #del his1["t"]
                                    #del his1["QryIndex"]
                            
                                elif bartype=="TICKS":
                                    temphis["DateTime"]=datetime.strptime(his1['Date']+(" 0" if len(his1['FilledTime'])==5 else " ")+his1['FilledTime'],"%Y%m%d %H%M%S").replace(tzinfo=self.gmt)
                                elif bartype=="1K" or bartype=="3K" or bartype=="5K" or bartype=="15K":
                                    temphis["DateTime"]=datetime.strptime(his1['Date']+(" 0" if len(his1['Time'])==5 else " ")+his1['Time'],"%Y%m%d %H%M%S").replace(tzinfo=self.gmt)
                                else:
                                    temphis["DateTime"]=datetime.strptime(his1['Date']+" 070000","%Y%m%d %H%M%S").replace(tzinfo=self.gmt)
                                #cnt = pytz.timezone('Asia/Shanghai')
                                #temphis["DateTime"]=temphis["DateTime"].astimezone(tz=cnt)
                                temphis.update(his1)
                                temp.append(temphis)
                        else:
                            self.status.remove({'DataType': m_type, 'StartTime':startTime, 'EndTime':endTime,'Symbol': symbol, 'Status': 'Ready'})
                            self.UnsubHistory(symbol, bartype, startTime, endTime)
                            break
                    return temp


    #解订历史数据
    #1：SessionKey，
    #2：合约代码，
    #3：数据周期:
        # tick: "TICKS",
        # 分K: "1K",
        # 日K: "DK"，
        # DOGS秒："DOGSS",
        # DOGS分K："DOGSK"
    #4: 历史数据开始时间,
    #5: 历史数据结束时间   
    def UnsubHistory(self, symbol, type, startTime, endTime):
        if not (re.match("TC.S.", symbol) or re.match("TC.F.", symbol) or re.match("TC.O.", symbol) or\
        re.match("TC.SP.", symbol) or re.match("TC.F2.", symbol) or re.match("TC.O2.", symbol)):
            print("合约代码格式错误")
            return
        if type=="3K" or type=="5K" or type=="15K":
            m_type="1K"
        else:
            m_type=type
        self.lock.acquire()
        obj = {"Request":"UNSUBQUOTE","SessionKey":self.qsessionKey}
        obj["Param"] = {"Symbol": symbol,"SubDataType":m_type,"StartTime" :startTime,"EndTime" :endTime}
        self.qsocket.send_string(json.dumps(obj))
        message = self.qsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        if symbol+type in self.lasthistorydata.keys():
            del self.lasthistorydata[symbol+type]
        return data

    def getstatus(self,symbol, bartype, startTime, endTime,dbtype):
        #st={}
        if bartype=="3K" or bartype=="5K" or bartype=="15K":
            m_type="1K"
        else:
            m_type=bartype
        st={'DataType': m_type, 'StartTime':startTime, 'EndTime':endTime,'Symbol': symbol, 'Status': 'Ready'}
        if self.status and st in self.status:
            return 'Ready'
        else:
            return ""

    def gethistorymulti(self,symbol, type, startTime, endTime,dbtype=""):
        th=[]
        result=[]
        if not isinstance(symbol, list):
            symbol=[symbol]
        for symb in symbol:
            histhread=self.GethisThread(self.__gethis,symb, type, startTime, endTime,dbtype)
            th.append(histhread)
            histhread.start()
        for th1 in th:
            result.append(th1.get_result())
        return result
    def __gethis(self,symbol, bartype, startTime, endTime='time.strftime("%Y%m%d",time.localtime())+"07"',dbtype=""):
        self.__subHistory(symbol, bartype, startTime, endTime,dbtype)
        if bartype=="3K" or bartype=="5K" or bartype=="15K":
            m_type="1K"
        else:
            m_type=bartype
        while True:
            if self.getstatus(symbol, bartype, startTime, endTime,dbtype)=='Ready':
                temp=[]
                if dbtype=="ODBC":
                    if bartype=="DOGSK" or bartype=="DOGSS":
                        # 使用 cursor() 方法创建一个游标对象 cursor
                        temp.append('Ready')
                        return temp
                    else:
                        print("只有DOGSK和DOGSS周期支持ODBC")
                        return None
                #his=self.gethistory(symbol, bartype, startTime, endTime)
                last=""

                while True:
                    his=self.__get_history(symbol, bartype, startTime, endTime,last)
                    if his and len(his["HisData"])>0:
                        last=his["HisData"][-1]['QryIndex']
                        temp=temp+his["HisData"]
                    else:
                        self.status.remove({'DataType': m_type, 'StartTime':startTime, 'EndTime':endTime,'Symbol': symbol, 'Status': 'Ready'})
                        self.UnsubHistory(symbol, bartype, startTime, endTime)
                        break
                return temp
    def __subHistory(self,symbol, type, startTime, endTime='time.strftime("%Y%m%d",time.localtime())+"07"',dbtype=""):
        if not (re.match("TC.S.", symbol) or re.match("TC.F.", symbol) or re.match("TC.O.", symbol) or\
        re.match("TC.SP.", symbol) or re.match("TC.F2.", symbol) or re.match("TC.O2.", symbol)):
            print("合约代码格式错误")
            return        
        if type=="3K" or type=="5K" or type=="15K":
            m_type="1K"
        else:
            m_type=type

        obj = { "Request":"SUBQUOTE",
                "SessionKey":self.qsessionKey,
                "Param":{   "Symbol": symbol,
                            "SubDataType":m_type,
                            "StartTime" :startTime,
                            "EndTime" :endTime,
                            "DBType":dbtype
                        }
                }
        self.lock.acquire()
        self.qsocket.send_string(json.dumps(obj))
        message = self.qsocket.recv()[:-1]
        self.lock.release()
        data = json.loads(message)
        return data
    #分页获取订阅的历史数据
    def __get_history(self,symbol, type, startTime, endTime, qryIndex=""):
        if type=="3K":
            m_type="1K"
            duration="3"
        elif type=="5K":
            m_type="1K"
            duration="5"
        elif type=="15K":
            m_type="1K"
            duration="15"
        else:
            m_type=type
            duration="1"
        obj = {"Request":"GETHISDATA",
            "SessionKey":self.qsessionKey,
            "Param":{"Symbol": symbol,
                    "SubDataType":m_type,
                    "Duration":duration,
                    "StartTime" :startTime,
                    "EndTime" :endTime,
                    "QryIndex" :qryIndex
                    }
                }

        self.lock.acquire()
        self.qsocket.send_string(json.dumps(obj))
        message = self.qsocket.recv()[:-1].decode("utf-8")
        self.lock.release()
        index =  re.search(":",message).span()[1]  # filter
        message = message[index:]
        #print(message)
        message = json.loads(message)
        return message

       
    #最新的K线数据
    def barupdate(self,symbol, bartype):
        if not (re.match("TC.S.", symbol) or re.match("TC.F.", symbol) or re.match("TC.O.", symbol) or\
        re.match("TC.SP.", symbol) or re.match("TC.F2.", symbol) or re.match("TC.O2.", symbol)):
            print("合约代码格式错误")
            return
        if symbol+type in self.lasthistorydata.keys():
            lastobj=self.lasthistorydata[symbol+type]

            if bartype=="3K":
                m_type="1K"
                duration="3"
            elif bartype=="5K":
                m_type="1K"
                duration="5"
            elif bartype=="15K":
                m_type="1K"
                duration="15"
            else:
                m_type=bartype
                duration="1"
            temp=[]
            self.lock.acquire()
            obj = {"Request":"GETHISDATA","SessionKey":self.qsessionKey}
            obj["Param"] = {"Symbol": symbol,"SubDataType":m_type,"Duration":duration,"StartTime" :lastobj["StartTime"],"EndTime" :lastobj["EndTime"],"QryIndex" :lastobj["lastindex"]}
            self.qsocket.send_string(json.dumps(obj))
            message = (self.qsocket.recv()[:-1]).decode("utf-8")
            self.lock.release()
            index =  re.search("{",message).span()[0]  # filter
            message = message[index:]
            message = json.loads(message)
            return message["HisData"]
        else:
            return

    #最新的K线数据
    def barupdate2(self,bartype,hisdata,realdata):
        if realdata['DataType']=='REALTIME' and realdata['Quote']["Symbol"]==hisdata[-1]['Symbol'] and  (int(realdata['Quote']['FilledTime'])+80000)<int(realdata['Quote']['CloseTime']):
            realdata['Quote']["DateTime"]=datetime.strptime(realdata['Quote']['TradeDate']+(" 0" if len(realdata['Quote']['FilledTime'])==5 else " ")+realdata['Quote']['FilledTime'],"%Y%m%d %H%M%S").replace(tzinfo=self.gmt)
            #print(realdata['Quote']["DateTime"])
            if bartype=="DK":
                if realdata['Quote']["DateTime"].date()==hisdata[-1]["DateTime"].date():
                    hisdata[-1]['Open']=realdata['Quote']["OpeningPrice"]
                    hisdata[-1]['High']=realdata['Quote']["HighPrice"]
                    hisdata[-1]['Low']=realdata['Quote']["LowPrice"]
                    hisdata[-1]['Close']= realdata['Quote']["TradingPrice"]
                    hisdata[-1]['Volume']= realdata['Quote']["TradeVolume"]
                elif realdata['Quote']["DateTime"].date()>hisdata[-1]["DateTime"].date():
                    temp={}
                    
                    temp['Symbol']=realdata['Quote']["Symbol"]
                    temp['DateTime']=realdata['Quote']["DateTime"]
                    temp['Date']=realdata['Quote']['TradeDate']
                    temp['Time']=realdata['Quote']["FilledTime"]
                    temp['UpTick']="0"
                    temp['UpVolume']="0"
                    temp['DownTick']="0"
                    temp['DownVolume']="0"
                    temp['UnchVolume']="0"

                    temp['Open']=realdata['Quote']["OpeningPrice"]
                    temp['High']=realdata['Quote']["HighPrice"]
                    temp['Low']=realdata['Quote']["LowPrice"]
                    temp['Close']= realdata['Quote']["TradingPrice"]
                    temp['Volume']= realdata['Quote']["TradeVolume"]
                    temp['QryIndex']= str(int(hisdata[-1]['QryIndex'])+1)

                    hisdata.append(temp)
            elif bartype=="1K" or bartype=="3K" or bartype=="5K" or bartype=="15K":
                duration=float(bartype.strip("K"))
                if hisdata[-1]["DateTime"]<=realdata['Quote']["DateTime"]:
                    temp={}
                    
                    temp['Symbol']=realdata['Quote']["Symbol"]
                    temp['DateTime']=hisdata[-1]["DateTime"]+timedelta(minutes=duration)
                    temp['Date']=hisdata[-1]["Date"]
                    temp['Time']=str(temp['DateTime'].hour*10000+temp['DateTime'].minute*100+temp['DateTime'].second)
                    temp['UpTick']="0"
                    temp['UpVolume']="0"
                    temp['DownTick']="0"
                    temp['DownVolume']="0"
                    temp['UnchVolume']="0"

                    temp['Open']=realdata['Quote']["TradingPrice"]
                    temp['High']=realdata['Quote']["TradingPrice"]
                    temp['Low']=realdata['Quote']["TradingPrice"]
                    temp['Close']= realdata['Quote']["TradingPrice"]
                    temp['Volume']= realdata['Quote']["TradeQuantity"]
                    if "OpenInterest" in realdata['Quote'].keys():
                        temp['OI']= realdata['Quote']["OpenInterest"]
                    else:
                        temp['OI']=""
                    temp['QryIndex']= str(int(hisdata[-1]['QryIndex'])+1)
                    hisdata.append(temp)
                else:
                    if  hisdata[-1]['High']<realdata['Quote']["TradingPrice"]:
                        hisdata[-1]['High']=realdata['Quote']["TradingPrice"]
                    elif hisdata[-1]['Low']>realdata['Quote']["TradingPrice"]:
                        hisdata[-1]['Low']=realdata['Quote']["TradingPrice"]
                    hisdata[-1]['Close']= realdata['Quote']["TradingPrice"]
                    hisdata[-1]['Volume']= str(int(hisdata[-1]['Volume'])+int(realdata['Quote']["TradeQuantity"]))
                    if "OpenInterest" in realdata['Quote'].keys():
                        hisdata[-1]['OI']= realdata['Quote']["OpenInterest"]
            elif bartype=="TICKS" :
                temp['Symbol']=realdata['Quote']["Symbol"]
                temp['DateTime']=realdata['Quote']["DateTime"]
                temp['Date']=hisdata[-1]["Date"]                
                temp['FilledTime']=realdata['Quote']['FilledTime']
                temp['TradeQuantity']=realdata['Quote']['TradeQuantity']
                temp['TradeVolume']=realdata['Quote']['TradeVolume']
                temp['Bid']=realdata['Quote']['Bid']
                temp['Ask']=realdata['Quote']['Ask']
                temp['TradingPrice']=realdata['Quote']['TradingPrice']
                temp['PreciseTime']=realdata['Quote']['PreciseTime'] 
                temp['OI']=realdata['Quote']['OpenInterest']
                temp['QryIndex']=str(int(hisdata[-1]['QryIndex'])+1)

        return hisdata



            


            
    #获取热门月历史对应的指定月数据
    #参数：
    #####symbol：TC.F.SHFE.rb.HOT
    #####Time:
    #        "20220105013000" yyyymmddHHMMSS带入该参数返回参数指定时间HOT对应的指定月{'20211116070001': 'TC.F.SHFE.rb.202205'}，其中Key为换月时间，Value为对应的指定月合约    
    #        ""不带入该参数时，返回HOT所有历史的换月记录
    def GetHotChange(self, symbol, Time=""):
        self.lock.acquire()
        obj = {"Request":"GETHOTCHANGE","SessionKey":self.qsessionKey}
        obj["Param"] = {"Symbol": symbol,"Time" :Time,}
        self.qsocket.send_string(json.dumps(obj))
        message = self.qsocket.recv()[:-1]
        self.lock.release()
        data = json.loads(message)
        return data['Info']
    #获取指定月份期权的实值、平值、虚值期权合约
    ####symbol:string 对应月份任意期权合约代码
    ####ATMIndex：int
        '''
        ....
        -2:实值两档期权合约
        -1:实值一档期权合约
         0:平值期权合约
         1:虚值期权合约
         .
         ..
        '''
    def GetATM(self, symbol, ATMIndex):
        self.lock.acquire()
        obj = {"Request":"GETATM","SessionKey":self.qsessionKey}
        obj["Param"] = {"Symbol": symbol,"ATMIndex" : ATMIndex}
        self.qsocket.send_string(json.dumps(obj))
        message = self.qsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        if data['Success']=='OK':
            return data['Info']['Result']
        else:
            return

    def quote_sub_th(self,sub_port,filter = ""):
        socket_sub = self.context.socket(zmq.SUB)
        #socket_sub.RCVTIMEO=7000
        #print(sub_port)
        socket_sub.connect("tcp://127.0.0.1:%s" % sub_port)
        socket_sub.setsockopt_string(zmq.SUBSCRIBE,filter)
        #strQryIndex ={}

        while(threading.main_thread().is_alive()):

            message = (socket_sub.recv()[:-1]).decode("utf-8")
            index =  re.search(":",message).span()[1]  # filter
            message = message[index:]
            message = json.loads(message)
            if(message["DataType"]=="TICKS" or message["DataType"]=="1K" or message["DataType"]=="DK" or message["DataType"]=="DOGSK"  or message["DataType"]=="DOGSS"):
                #del message['StartTime']
                #del message['EndTime']
                if 'DBType' in message.keys():
                    del message['DBType']
                if message not in self.status:
                    self.status.append(message)
            elif message['DataType']!= 'PING':
                self.eventQueue.put(message)
                if message['DataType']=='REALTIME':
                    self.realdate[message['Quote']['Symbol']]=message['Quote']['TradeDate']
        return

    #查询合约信息
    def QueryInstrumentInfo(self, symbol):
        self.lock.acquire()
        obj = {"Request" : "QUERYINSTRUMENTINFO" , "SessionKey" : self.qsessionKey , "Symbol" : symbol}
        self.qsocket.send_string(json.dumps(obj))
        message = self.qsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    #查询对应类型的所有合约
    #"Type":
    #期货：Future
    #期权：Options
    #证券：Stock
    def QueryAllInstrumentInfo(self, type,dt=""):
        self.lock.acquire()
        obj = {"Request": "QUERYALLINSTRUMENT", "SessionKey": self.qsessionKey, "Type": type, "DateTime": dt}
        self.qsocket.send_string(json.dumps(obj))
        message = self.qsocket.recv()[:-1]
        data = json.loads(message)
        self.lock.release()
        return data

    def CreatePingPong(self, sessiondata,stkobj):
        #if self.m_objZMQKeepAlive != None:
        #    self.m_objZMQKeepAlive.Close()
        self.m_objZMQKeepAlive = KeepAliveHelper(sessiondata,self,stkobj)
        
        return
    class GethisThread(threading.Thread):
        def __init__(self, func,symbol, type, startTime, endTime,dbtype):
            threading.Thread.__init__(self)
            self.funct=func
            self.symb=symbol
            self.bartype=type
            self.startt=startTime
            self.endt=endTime
            self.db=dbtype
            self.result=None

        def run(self):
            self.result =self.funct(self.symb,self.bartype,self.startt,self.endt,self.db)

        def get_result(self):
            threading.Thread.join(self) # 等待线程执行完毕
            try:
                return self.result
            except Exception:
                return None

#心跳相关
class KeepAliveHelper():
    def __init__(self, sessiondata, objZMQ, stkobj):
        self.IsTerminal = False
        self.socket=None
        self.subPort=sessiondata["SubPort"]
        self.sessionKey=sessiondata["SessionKey"]
        self.tzmqobj=objZMQ
        self.socketobj=stkobj
        threading.Thread(target = self.ThreadProcess, args=()).start()
        
    def Close(self):
        self.IsTerminal = True

    #连线心跳（在收到"PING"消息时调用）
    def Pong(self,id = ""):
        if not self.tzmqobj.LoginOK:
            return ""
        self.tzmqobj.lock.acquire()
        obj = {"Request":"PONG","SessionKey": self.sessionKey, "ID":id}
        self.socketobj.send_string(json.dumps(obj))
        message = self.socketobj.recv()[:-1]
        data = json.loads(message)
        self.tzmqobj.lock.release()
        return data

    def ThreadProcess(self):
        socket_sub = zmq.Context().socket(zmq.SUB)
        socket_sub.connect("tcp://127.0.0.1:%s" % self.subPort)
        socket_sub.setsockopt_string(zmq.SUBSCRIBE,"")
        while threading.main_thread().is_alive():
            message = (socket_sub.recv()[:-1]).decode("utf-8")
            findText = re.search("{\"DataType\":\"PING\"}",message)

            if findText == None:
                continue

            if self.IsTerminal:
                return
            self.Pong("TC")

class TCoreZMQ(TradeClass,QuoteClass):
    def __init__(self,APPID="ZMQ",SKey="8076c9867a372d2a9a814ae710c256e2",quote_port="51864",trade_port="51834",logpath=""):
        TradeClass.__init__(self)
        QuoteClass.__init__(self)
        self.trade_connect(APPID,SKey,trade_port)
        self.quote_connect(APPID,SKey,quote_port)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level = logging.INFO)
        if logpath:
            handler = logging.FileHandler(logpath)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    def log(self,message):
        if self.logger:
            self.logger.info(message)
            