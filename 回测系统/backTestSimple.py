class backTestSimple():
    def __init__(self, stragy = None, tradeSys = tradeSystemSimple(), start_date = None, end_date = None, frequency = '1d', 
                 risk_free_rate = 0.02, init_cash = None):

        self.risk_free_rate = risk_free_rate
        self.start_date = start_date
        self.end_date = end_date
        self.frequency = frequency        
        tradeSys.context.portfolio.init_cash = init_cash #初始化账户
        tradeSys.context.portfolio.available_cash = init_cash #初始化账户
        tradeSys.context.portfolio.total_value = init_cash #初始化账户
        self.tradeSys = tradeSys
        self.stragy_m = stragy
        self.index = '000001.XSHG'
    
    '''回测驱动'''    
    def start(self, context):
        #获取回测频率
        stragy_m = self.stragy_m
        context.frequency = self.frequency
        df_data = get_price(self.index, start_date = self.start_date, end_date=self.end_date, frequency = self.frequency)
        trade_frequency = df_data.index
        stragy_m.initialize(context)
        for trade_delta in trade_frequency:
            log.info('开始新的一轮，时间：{}'.format(trade_delta))
            context.current_dt = trade_delta          
            stragy_m.before_trading(context)
            stragy_m.handle(context)
            #stragy_m.after_trading(context)
        #self.estimate()   
        #self.visualize()
        
    
    '''回测可视化'''
    def visualize(self):
        df = pd.DataFrame(self.tradeSys.gain_records, columns=['date', 'total_value', 'nav', 'bench_price'])
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)
        df['bench_nav'] = df['bench_price'] / df['bench_price'][0]
        plt.figure(figsize=(12,6))
        plt.plot(df.index, df['nav'], color='pink', label='策略收益')
        plt.plot(df.index, df['bench_nav'], color='red', label='基准收益')
        plt.axhline(0,ls='--')
        plt.title('回测收益曲线图')
        plt.xlabel('时间（单位：天）')
        plt.ylabel('收益')
        plt.legend()

    
    '''策略评估目前产出：最大回撤，夏普比率，胜率，beta，alpha，待补充'''
    def estimate(self):
        df = pd.DataFrame(self.tradeSys.gain_records, columns=['date', 'total_value', 'nav', 'bench_price'])
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)
        max_down_rate, max_down_start, max_down_end = self.get_max_down(df)
        sharp_ratio = self.get_sharp_ratio(df)
        win_ratio = self.get_win_ratio(df)
        beta = self.get_Beta(df)
        alpha = self.get_alpha(df)        
    
    '''获取最大回撤'''       
    def get_max_down(self, df):
      
        df['max_nav'] = df['nav'].expending().max()
        df['down_rate'] = df['nav'] / df['max_nav']
        max_down_rate = df['down_rate'].sort_values(['down_rate'], 
                                ascending = True).iloc[[0],df.columns.get_loc('down_rate')]
        min_down_rate = df[df.index < max_down_rate.index[0]].sort_values(['down_rate'], 
                                ascending = False).iloc[[0],df.columns.get_loc('down_rate')]
        min_down = df[df['max_dows_rate'] < max_down].sort_values(['max_dows_rate'], 
                                ascending = False).iloc[[0],df.columns.get_loc('max_dows_rate')]       
        max_down = 1 - max_down_rate.values #最大回撤
        max_down_start = min_down.index[0] #最大回撤开始日期
        max_down_end = max_down.index[0] #最大回撤结束日期
        return max_down, max_down_start, max_down_end
        
    '''获取夏普比率'''    
    def get_sharp_ratio(self, df):
        '''
         夏普率衡量的是风险和收益的平衡
         使用过程中，分为两种，一种是事先夏普率，另一种是事后夏普率，
         事先夏普率：组合收益率、无风险收益率、组合波动率是预期数据。
         事后夏普率：组合收益率、无风险收益率、组合波动率是历史数据。
         事后夏普率计算方式有不同的标准，其时间频率是年华夏普比率。
         方式一：（日均收益率-无风险收益率）/ 组合标准差   * sqr（252）
         方式二：超额收益的日均值 / 组合标准差   * sqr（252）
         本方法采用第二种方式
        '''
        #超额收益
        df['excess_income'] = df['nav'].pct_change().fillna(0.0) - df['bench_price'].pct_change().fillna(0.0)
        excess_income_mean = df['excess_income'].mean()
        excess_income_volatility =  df['excess_income'].std()
        return excess_income_mean.div(excess_income_volatility) * np.sqrt(252)
    
    '''计算赢率'''
    def get_win_ratio(self, df):
        
        df['income_rate'] = df['nav'].pct_change().fillna(0)
        win_num = df[df['income_rate'] > 0].shape[0]
        return win_num / df.shape[0]
    
    '''计算beta值'''
    def get_Beta(self, df):
        '''
        计算Beta值的方式有两种
        种类一：公式法，Cov（标的，基准）/ Var（基准）
        种类二：线性回归，标的收益 = Rf + beta * （标的收益 - 基准收益）
        本方法采用公式法
        '''
        df['income_rate'] = df['nav'].pct_change().fillna(0.0)
        df['bench_rate'] = df['bench_price'].pct_change().fillna(0.0)
        return np.cov(df['income_rate'], df['bench_rate']) / np.var(df['bench_rate'])
    
    '''计算alpha值'''
    def get_alpha(self, df):
        beta = self.get_Beta(df)
        a_return = self.aunual_return(df)
        bench_return = self.aunual_beach_return(df)
        return (a_return - self.risk_free_rate - beta(bench_return - self.risk_free_rate))
    
    '''计算策略年化收益率'''
    def aunual_return(self, df):
        stragy_return = df['nav'][-1:]/df['nav'][0] -1
        a_return = ((stragy_return + 1) ** (250/df.shape[0]) -1)
        return a_return
    
    '''计算基准年化收益率'''
    def aunual_beach_return(self, df):
        stragy_return = df['bench_price'][-1:]/df['bench_price'][0] -1
        a_return = ((stragy_return + 1) ** (250/df.shape[0]) -1)
        return a_return
        
             
