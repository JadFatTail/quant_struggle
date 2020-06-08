from . import tradeSystemSimple
from . import stragy_turtleTrade
tradeSys = tradeSystemSimple() #初始化交易系统
stragy = stragy_turtleTrade(tradeSys) #初始化策略
backTest = backTestSimple(stragy = stragy,tradeSys = tradeSys,start_date = '2019-01-01', end_date = '2019-06-01',frequency = '1m',  
                          init_cash = 100000.00) #设置回测条件
