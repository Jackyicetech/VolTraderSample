# VolTraderSample
本篇課程是透過python抓取VolTrader的即時或歷史數據並加以應用，每一篇文章對應一篇course檔案\
EX:https://www.touchance.com.tw/vt_post?idno=200 對應的是course1
# 環境準備
文章中有介紹需要使用window並安裝pycharm以及talib可以事先下載好，也可以根據文章一步一步執行下載安裝動作\
使用程式碼前需要先執行VolTrader，否則會回傳空值
# 程式碼
tcoreapi_mq裡存放著連接VolTrader、登出、訂閱報價、歷史數據等等的函式\
quote_functions裡則是可以更改即時報價輸出的資訊內容\
trade_functions除了下單、改單等功能外也可以查詢資金帳號
