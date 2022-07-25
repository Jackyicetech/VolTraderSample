from pymongo import MongoClient
from datetime import datetime
import pandas as pd
import numpy as np
from pandas import date_range
from exchange_calendars import get_calendar
from vnpy.trader.object import BarData
from vnpy.trader.database import database_manager
from vnpy.trader.constant import Interval, Exchange


def save_daily_data(data, collection_name):
    bars = []

    for row in data:
        bar = BarData(
            symbol="VolTrader",
            exchange=Exchange.TFE,
            datetime=datetime.strptime(row['Date'], '%Y-%m-%d'),
            interval=Interval.DAILY,
            volume=row['Volume'],
            open_price=row['Open'],
            high_price=row['High'],
            low_price=row['Low'],
            close_price=row['Close'],
            gateway_name='DB'
        )

        bars.append(bar)

    database_manager.save_bar_data(bars, collection_name)


def read_history(date):
    output = []

    date_str = np.int64(date.strftime('%Y%m%d'))
    data = pd.read_csv("history_data.csv")

    for i in range(len(data)):
        if date_str == data["Date"][i]:
            o, h, l, c, v = [x for x in data.iloc[i][7:12]]

            output.append({
                'Date': date.strftime('%Y-%m-%d'),
                'Open': o,
                'High': h,
                'Low': l,
                'Close': c,
                'Volume': v,
            })

    return output


def upload_daily_data(collection_name, start_date=datetime(2018, 1, 1), end_date=datetime(2022, 7, 15)):
    dates = date_range(start_date, end_date)

    tw_calendar = get_calendar('XTAI')

    for date in dates:

        if date in tw_calendar.opens:

            VolTrader_data = read_history(date)

            if VolTrader_data:
                save_daily_data(VolTrader_data, collection_name)
                print(f'Update {date} historical price of VolTrader success')
            else:
                print(f'No VolTrader data found on {date}')


upload_daily_data('VolTrader')
