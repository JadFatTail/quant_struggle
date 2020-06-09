class stragy_turtleTrade():
    def __init__(self, tradeSys = None):
        self.tradeSys = tradeSys
        
        
    def initialize(self, context):
        #setCommission(context)
        self.set_params()
        
    def set_params(self):
       
        self.tar_stock = '000725.XSHE'
        self.unit = None #仓位粒度
        self.unit_limit = 4 #仓位控制限制
        self.break_price = None #买入线
        self.N_step = 20
        self.turtle = turtleTrading(N_step = 20)
    
    def set_commission(self):
        dt = context.current_dt
        if dt>datetime.datetime(2013,1, 1):
            set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5)) 

        elif dt>datetime.datetime(2011,1, 1):
            set_commission(PerTrade(buy_cost=0.001, sell_cost=0.002, min_cost=5))

        elif dt>datetime.datetime(2009,1, 1):
            set_commission(PerTrade(buy_cost=0.002, sell_cost=0.003, min_cost=5))

        else:
            set_commission(PerTrade(buy_cost=0.003, sell_cost=0.004, min_cost=5))
            
    def before_trading(self, context):
        #set_slippage(FixedSlippage(0)) #设置滑点
        #setCommission() #设置手续费
        pd.to_datetime(str(context.current_dt))
        current_dt = context.current_dt
        current_date = current_dt.strftime('%Y-%m-%d')
        history_data = get_price(self.tar_stock, end_date = current_date, frequency='daily', fields=('high','low','close'), skip_paused=True, fq='pre', 
                      count = self.N_step + 1, panel=False)
        self.turtle.get_volatility(history_data[:-1]) #计算加权移动波动
        self.turtle.get_tqa_line(history_data[:-1]) #计算唐奇安通道上、中、下轨
        
    def handle(self, context):

        total_value = context.portfolio.total_value #获取账户市值
        available_cash = context.portfolio.available_cash #账户现金余额
        volatility = self.turtle.volatility[-1] * 1
        self.unit = (total_value * 0.01) / volatility #当前波动下，最大单次损失1%的购买量
        log.info('时间：{},市值:{}, 波动:{}, 待加仓数量{}'.format(context.current_dt, total_value, volatility, self.unit))
        #current_dt = context.current_dt
        #price_data = get_price(tar_stock, end_date = current_dt, frequency = '1m', count=1)    
        price_data = get_price(self.tar_stock, end_date = context.current_dt, frequency = '1m', count=1)
        if len(context.portfolio.positions) == 0:
            self.market_in(context, price_data['close'].values[-1]) #开仓买入
        else:
            self.stop_loss(context, price_data['close'].values[-1]) #止损
            #self.stop_gain(context, price_data['close']) #止赢
            self.market_add(context, price_data['close'].values[-1]) #加仓
            self.market_out(context, price_data['close'].values[-1]) #出局
    
    '''利用唐奇安通道，上传上轨突破视为开仓信号'''
    def market_in(self, context, current_price):  
        
        # 当前价格突破唐奇安通道上轨
        log.info('时间：{}，current_price:{}, self.turtle.tqa_high[-1]:{}'.format(context.current_dt, current_price, self.turtle.tqa_high[-1]))
        if current_price > self.turtle.tqa_high[-1]:
            available_cash = context.portfolio.available_cash        
            tobuy_shares = available_cash / current_price #计算当前可买量
            if tobuy_shares >= self.unit: 
                log.info('时间：{}，开仓，买入股票:{}:股票数量{}'.format(context.current_dt, self.tar_stock, self.unit))
                order_info = self.tradeSys.order(self.tar_stock, self.unit)
                if order_info:
                    if str(order_info['status']) == 'S':
                        log.info('下单成功！！')
                        self.break_price = current_price
                        
    '''再买入价基础上，股价突破break_price + 0.5*volatility，视为有效突破'''
    def market_add(self, context, current_price): 
        log.info('market_add 时间：{}，self.break_price:{}, 0.5 * volatility:{}'.format(context.current_dt, self.break_price, 0.5 * self.turtle.volatility[-1]))        
        if current_price >= (self.break_price + 0.5 * self.turtle.volatility[-1]):
            cash = context.portfolio.available_cash
            tobuy_shares = cash / current_price
            log.info('时间：{}，股票突破半个波动，可购买股票数量：{}，买入前持仓:{}，限量{}'.format(context.current_dt, tobuy_shares, context.portfolio.positions[self.tar_stock], self.unit_limit * self.unit))
            if ((tobuy_shares > self.unit) and              
                (context.portfolio.positions[self.tar_stock] < (self.unit_limit * self.unit))):  
                log.info('时间：{}，加仓，买入股票:{}:股票数量{}'.format(context.current_dt, self.tar_stock, self.unit))
                order_info = self.tradeSys.order(self.tar_stock, self.unit)
                if order_info:
                    if str(order_info['status']) == 'S':
                        log.info('下单成功！！')
                        self.break_price = current_price
    '''股价跌破唐奇安中轨，视为打开下降通道，需要全部卖出'''
    def market_out(self, context, current_price): 
        log.info('market_out 时间：{}，current_price:{}, self.turtle.tqa_high[-1]:{}'.format(context.current_dt, current_price, self.turtle.tqa_high[-1]))
        if current_price <= self.turtle.tqa_middle[-1]:
            log.info('跌破中轨，离场')
            order_info = self.tradeSys.order_target(self.tar_stock, 0)
            if order_info:
                if str(order_info['status']) == 'S':
                    log.info('清仓成功！！')
                    
    '''股价回调至最后买入价下方两个单位的波动，则清仓止损'''                      
    def stop_loss(self, context,current_price):
        log.info('stop_loss 时间：{}，current_price:{}, self.turtle.tqa_high[-1]:{}'.format(context.current_dt, current_price, self.turtle.tqa_high[-1]))
        if current_price < (self.break_price - (2 * self.turtle.volatility[-1])):
            log.info('时间：{}，清仓，股票:{}'.format(context.current_dt, self.tar_stock))
            order_info = self.tradeSys.order_target(self.tar_stock, 0)
            if order_info:
                if str(order_info['status']) == 'S':
                    log.info('清仓成功成功！！')
