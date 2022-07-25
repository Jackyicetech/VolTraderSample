from pandas import date_range
from trading_calendars import get_calendar
from datetime import datetime
from pymongo import MongoClient

import time
import requests

from vnpy.trader.database import database_manager
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy.trader.setting import get_settings

header = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36'
    }


def get_json_data(url):

    for i in range(3):
        try:
            res = requests.get(url, headers=header)
            return res.json()
        except Exception as e:
            print('Max retries exceeded, waiting 45 seconds for next retry.')
            time.sleep(45)

    return None

def convert_to_float(x):

    try:
        if isinstance(x, str):
            if '-' in x:
                return float('nan')
        return float(str(x).replace(',', ''))
    except:
        return x

def save_daily_data(data, collection_name):

    bars = []
    
    for row in data:

        bar = BarData(
            symbol=row['Ticker'],
            exchange=Exchange.TSE,
            datetime=datetime.strptime(row['Date'], '%Y-%m-%d'),
            interval=Interval.DAILY,
            volume = row['Volume'],
            open_price = row['Open'],
            high_price = row['High'],
            low_price = row['Low'],
            close_price = row['Close'],
            gateway_name='DB'
            )
        
        bars.append(bar)

    database_manager.save_bar_data(bars, collection_name)


def get_tse_data(date):
    
    output = []
    
    date_str = date.strftime('%Y%m%d')
    url = f'https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date_str}&type=ALLBUT0999'
    
    for i in range(3):

        json_data = get_json_data(url)
    
        if not json_data:
            time.sleep(3)
            continue
            
        if 'data9' in json_data:   # 2011 某日才改變資料放的位置
            data = json_data['data9']
            break
        elif 'data8' in json_data:
            data = json_data['data8']
            break
  
    else:
        return None
        
    for k in range(len(data)):
        
        o,h,l,c,v = [convert_to_float(x) for x in data[k][5:9] + data[k][2:3]]
        
        output.append({
            'Date':date.strftime('%Y-%m-%d'),
            'Ticker':data[k][0],
            'Open':o,
            'High':h,
            'Low':l,
            'Close':c,
            'Volume':int(v),
        })
            
    return output

def get_otc_data(date):
    
    output = []
    
    date_str = str(date.year - 1911) + '/' + date.strftime('%m/%d')

    url = f'https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php?l=zh-tw&d={date_str}&se=EW'
    
    for i in range(3):

        json_data = get_json_data(url)
    
        if not json_data:
            time.sleep(3)
            continue
            
        if 'aaData' in json_data:
            data = json_data['aaData']
            break
        
    else:
        return None
    
    for k in range(len(data)):

        o,h,l,c,v = [convert_to_float(x) for x in data[k][4:7]+data[k][2:3]+data[k][7:8]]
        
        output.append({
            'Date':date.strftime("%Y-%m-%d"),
            'Ticker':data[k][0],
            'Open':o,
            'High':h,
            'Low':l,
            'Close':c,
            'Volume':int(v),
        })

    return output

def update_daily_data(collection_name):
    
    config = get_settings()
    
    database_name = config['database.database']
    ip = config['database.host']
    port = config['database.port']
    
    client = MongoClient(f'mongodb://{ip}:{port}') # 依照vnpy中設定的database的ip與port
    
    database = client[database_name]
    collection = database[collection_name]
    num_docs = collection.estimated_document_count()
        
    if num_docs > 0:
        start_date = list(collection.distinct('datetime'))[-1]
    else:
        start_date = datetime(2004, 2, 11) # 此日期為證交所公告最早的日期 2004-02-11
        
    end_date = datetime.today() # 最後一日皆設定執行的當日
    dates = date_range(start_date, end_date)

    tw_calendar = get_calendar('XTAI')

    for date in dates:

        if date in tw_calendar.opens:
        
            try:
                tse_data = get_tse_data(date)

                if tse_data:
                    save_daily_data(tse_data, collection_name)
                    print(f'Update {date} historical price of tse success')
                else:
                    print(f'No tse data found on {date}')

            except Exception as e:
                print(f'[{date}] Unexpected error:', e)

            if date >= datetime(2007, 7, 1): # 上櫃股票行情從 2007-07-01 開始有資料
                
                try:
                    otc_data = get_otc_data(date)

                    if otc_data:
                        save_daily_data(otc_data, collection_name)
                        print(f'Update {date} historical price of otc success')
                    else:
                        print(f'No otc data found on {date}')

                except Exception as e:
                    print(f'[{date}] Unexpected error:', e)

            time.sleep(3)