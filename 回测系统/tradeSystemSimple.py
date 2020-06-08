class portfolio():
    def __init__(self):
        self.positions = {}
        self.available_cash = None
        self.total_value = None
        self.init_cash = None

class context():
    def __init__(self):
        self.portfolio = portfolio()
        self.current_dt = None
        self.frequency = None

class tradeSystemSimple():
    def __init__(self, init_cash = None):
        '''创建账户数据结构'''
        #self.init_cash = init_cash
        #账户持仓情况，字典数据类型;可用余额;市值
        self.context = context()
        
        '''创建与下单相关数据结构'''
        self.order_info = {}
        self.trade_records = []
        self.gain_records = []
        
    '''按目标股数下单,tar_stock_num为目标持股数据量'''
    def order_target(self, stock, tar_stock_num):
        order_info = {} #存放下单状态
        hold_stock_num = self.context.portfolio.positions[stock]
       
        if tar_stock_num == 0:    
            sail_stock_num = self.context.portfolio.positions[stock]
            stock_price = get_price(stock, end_date = self.context.current_dt, 
                                frequency = self.context.frequency, count = 1)['close'].values[-1]
            #todo 增加手续费和滑点
            self.context.portfolio.available_cash += self.context.portfolio.positions[stock] * stock_price
            del self.context.portfolio.positions[stock]
            log.info('清仓成功，卖出股票:{}:股票数量{},股票价格:{},可用余额:{},市值:{}'.format(stock, sail_stock_num,
                                    stock_price, self.context.portfolio.available_cash, self.total_value(stock)))
            self.record_trade(stock, 'S', sail_stock_num)
            order_info['status'] = 'S'
            return order_info
        elif (hold_stock_num > tar_stock_num):
            sail_stock_num = math.floor((hold_stock_num - tar_stock_num)/100) * 100
            self.context.portfolio.positions[stock] -= sail_stock_num
            #todo 增加手续费和滑点
            stock_price = get_price(stock, end_date = self.context.current_dt, 
                                frequency = self.context.frequency, count = 1)['close'].values[-1]
            self.context.portfolio.available_cash += sail_stock_num * stock_price
            log.info('下单成功，卖出股票:{}:股票数量{},股票价格:{},可用余额:{},市值:{}'.format(stock, sail_stock_num,
                                    stock_price, self.context.portfolio.available_cash, self.total_value(stock)))
            self.record_trade(stock, 'S', sail_stock_num)
            order_info['status'] = 'S'
            return order_info
        else:
            buy_stock_num = math.floor((tar_stock_num - hold_stock_num)/100) * 100
            self.context.portfolio.positions[stock] += buy_stock_num
            #todo 增加手续费和滑点
            stock_price = get_price(stock, end_date = self.context.current_dt, 
                                frequency = self.context.frequency, count = 1)['close'].values[-1]
            self.context.portfolio.available_cash -= buy_stock_num * stock_price
            log.info('下单成功，买入股票:{}:股票数量{},股票价格:{},可用余额:{},市值:{}'.format(stock, buy_stock_num,
                                    stock_price, self.context.portfolio.available_cash, self.total_value(stock)))
            self.record_trade(stock, 'B', buy_stock_num)
            order_info['status'] = 'S'
            return order_info
        
    def order(self, stock, stock_num, benchmark = None):
        order_info = {} #存放下单状态
        
        buy_stock_num = math.floor( stock_num / 100) * 100
        if buy_stock_num > 0:
            if stock in self.context.portfolio.positions.keys():                
                self.context.portfolio.positions[stock] += buy_stock_num
            else:
                self.context.portfolio.positions[stock] = buy_stock_num
            #获取股票价格,todo增加撮合交易，手续费，滑点
            stock_price = get_price(stock, end_date = self.context.current_dt, 
                                frequency = self.context.frequency, count = 1)['close'].values[-1]
            self.context.portfolio.available_cash -= buy_stock_num * stock_price
            log.info('下单成功，买入股票:{}:股票数量{},股票价格:{},可用余额:{},市值:{}'.format(stock, buy_stock_num,
                        stock_price, self.context.portfolio.available_cash, self.total_value(stock)))
            self.record_trade(stock, 'B', buy_stock_num, benchmark)
            order_info['status'] = 'S'
            return order_info
        else:
            log.info('资金不足，下单失败')
            order_info['status'] = 'F'
            return order_info
    
    def total_value(self, stock):
        self.context.portfolio.total_value =self.context.portfolio.available_cash
        for stock in self.context.portfolio.positions.keys():
            stock_price = get_price(stock, end_date = self.context.current_dt, 
                                    frequency = self.context.frequency, count = 1)['close'].values[-1]
            self.context.portfolio.total_value += self.context.portfolio.positions[stock] * stock_price
        
        #log.info('self.context.portfolio.total_value:{}'.format(self.context.portfolio.total_value))
        return self.context.portfolio.total_value  
    
    '''当前频率结束，记录每个交易日账户情况'''
    def record_trade(self, stock, signal, stock_num, benchmark = None):
        
        total_value = self.total_value(stock)
        log.info('计算市值：{}'.format(total_value))
        nav = round((total_value / self.context.portfolio.init_cash), 2) # 计算持仓净值
        self.trade_records.append((self.context.current_dt, stock, signal, stock_num, self.total_value(stock), nav))
        if((self.context.current_dt.hour == 15) and (self.context.current_dt.minute == 0)):
            #nav = round((self.total_value(stock) / self.context.portfolio.init_cash), 2) # 计算持仓净值
            current_date = self.context.current_dt.strftime('%Y-%m-%d')
            bench_price = 0.00
            if benchmark:
                bench_price = get_price(benchmark, end_date = current_date, count = 1)['close'].values[-1]
            else:
                bench_price = get_price(stock, end_date = current_date, count = 1).values[-1]
            self.gain_records.append((current_date, self.total_value(stock), nav, bench_price))
            
    '''获取回测过程中交易记录'''
    def get_records(self):
        df = pd.DataFrame(self.trade_records, columns=['date', 'stock', 'signal', 'total_value', 'nav'])
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)
        return df
              
