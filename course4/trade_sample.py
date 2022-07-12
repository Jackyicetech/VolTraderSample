from tcoreapi_mq import *
from trade_functions import *
import threading

g_TradeZMQ = None
g_TradeSession = ""
ReportID = ""


def main():
    global g_TradeZMQ
    global g_TradeSession

    # 登入(與 VolTrader zmq 連線用，不可改)
    g_TradeZMQ = TradeAPI("ZMQ", "8076c9867a372d2a9a814ae710c256e2")
    t_data = g_TradeZMQ.Connect("51617")
    print(t_data)

    if t_data["Success"] != "OK":
        print("[trade]connection failed")
        return

    g_TradeSession = t_data["SessionKey"]

    #######################################################################交易##################################################
    # 建立一個交易執行緒
    t1 = threading.Thread(target=trade_sub_th, args=(g_TradeZMQ, t_data["SubPort"],))
    t1.daemon = True
    t1.start()
    # 查詢已登入資金帳號
    accountInfo = g_TradeZMQ.QryAccount(g_TradeSession)
    print("查詢已登入的資金帳號:", accountInfo)

    strAccountMask = ""
    if accountInfo is not None:
        arrInfo = accountInfo["Accounts"]
        if len(arrInfo) != 0:
            strAccountMask = arrInfo[0]["AccountMask"]
            print(strAccountMask)

            # 查詢委託紀錄
            reportData = g_TradeZMQ.QryReport(g_TradeSession, "")
            print('查詢所有回報:', reportData)
            # ShowEXECUTIONREPORT(g_TradeZMQ, g_TradeSession, reportData)
            fillReportData = g_TradeZMQ.QryFillReport(g_TradeSession, "")
            print('查詢成交回報:', fillReportData)
            # ShowFillReport(g_TradeZMQ, g_TradeSession, fillReportData)

            # 查詢資金
            if strAccountMask != "":
                print("查詢資金帳號：", g_TradeZMQ.QryMargin(g_TradeSession, strAccountMask))

            # 查詢持倉
            positionData = g_TradeZMQ.QryPosition(g_TradeSession, strAccountMask, "")
            print('查詢持倉部位:', positionData)
            ShowPOSITIONS(g_TradeZMQ, g_TradeSession, strAccountMask, positionData)

            # 下單
            orders_obj = {
                "Symbol": "TC.F.TWF.MXF.202209",
                "BrokerID": arrInfo[0]['BrokerID'],
                "Account": arrInfo[0]['Account'],
                "Price": "15000",
                "Side": "1",
                "OrderQty": "1",
                # "TimeInForce": "1",
                # "OrderType": "2",
                # "PositionEffect": "0"
            }
            # TimeInForce:
            # 1 : ROD
            # 2 : IOC/FAK
            # 3 : FOK
            # OrderType:
            # 1 : Market order
            # 2 : Limit order
            # 3 : Stop order
            # 4 : Stop limit order
            # 5 : Trailing Stop
            # 6 : Trailing StopLimit
            # 7 : Market if Touched Order
            # 8 : Limit if Touched Order
            # 9 : Trailing Limit
            # 10 : 對方價(HIT)
            # 11 : 本方價(JOIN)
            # 15 : 中間價(MID)
            # 20 : 最優價 (BST)
            # 21 : 最優價轉限價 (BSTL)
            # 22 : 五檔市價 (5LvlMKT)
            # 23 : 五檔市價轉限價 (5LvlMTL)
            # 24 : 市價轉限價 (MTL)
            # 25 : 一定範圍市價(MWP)
            # PositionEffect:
            # 0:新倉  Open position
            # 1:平倉  Close position
            # 4:自動   Auto select Open/Cloe position
            s_order = g_TradeZMQ.NewOrder(g_TradeSession, orders_obj)
            print('下單結果:', s_order)

            if s_order['Success'] == "OK":
                print("下單成功")
            elif s_order['ErrCode'] == "-10":
                print("unknown error")
            elif s_order['ErrCode'] == "-11":
                print("買賣別錯誤")
            elif s_order['ErrCode'] == "-12":
                print("複式單商品代碼解析錯誤 ")
            elif s_order['ErrCode'] == "-13":
                print("下單帳號,不可下此交易所商品")
            elif s_order['ErrCode'] == "-14":
                print("下單錯誤,不支持的 價格 或 OrderType 或 TimeInForce")
            elif s_order['ErrCode'] == "-15":
                print("不支援證券下單")
            elif s_order['ErrCode'] == "-20":
                print("未建立連線")
            elif s_order['ErrCode'] == "-22":
                print("價格的 TickSize 錯誤")
            elif s_order['ErrCode'] == "-23":
                print("下單數量超過該商品的上下限 ")
            elif s_order['ErrCode'] == "-24":
                print("下單數量錯誤 ")
            elif s_order['ErrCode'] == "-25":
                print("價格不能小於和等於 0 (市價類型不會去檢查) ")

            # 改單
            reporders_obj = {
                "ReportID": "2150302830A",
                "Price": "16500"
                # "ReplaceExecType": "0",
            }
            reorder = g_TradeZMQ.ReplaceOrder(g_TradeSession, reporders_obj)

            # 刪單
            print("%%%%%%%%%%%%%%%%%%%%%%%%%", reorder)
            canorders_obj = {
                "ReportID": "2104358805H",
            }
            canorder = g_TradeZMQ.CancelOrder(g_TradeSession, canorders_obj)
            print("%%%%%%%%%%%%%%%%%%%%%%%%%", canorder)
            g_TradeZMQ.Logout(g_TradeSession)


if __name__ == '__main__':
    main()
