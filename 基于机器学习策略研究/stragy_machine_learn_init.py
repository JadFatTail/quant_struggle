from jqdata import *
from jqlib.technical_analysis import *
from jqfactor import get_factor_values
from jqfactor import winsorize_med
from jqfactor import standardlize
from jqfactor import neutralize
import datetime
import pandas as pd
import numpy as np
from sklearn.svm import SVR 
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import KFold# 拟合训练集，生成模型
tools = private_tools()
class stragy_machine_learn_init():
    
    '''                         数据处理部分                                     '''
    '''获取相关因子'''
    def get_init_Factor(self, feasible_stocks, current_date):
        q = query(valuation.code, 
            valuation.market_cap,#估值因子-市值
            #估值因子
            valuation.pe_ratio, #市盈率（TTM）
            valuation.pb_ratio, #市净率（TTM）
            valuation.pcf_ratio, #市现率
            valuation.ps_ratio, #市销率
            balance.development_expenditure, #为市研率做准备
            balance.dividend_payable, #为股息率做准备
            #资本结构
            balance.total_assets - balance.total_liability, #净资产
            balance.total_assets / balance.total_liability, #财务杠杆
            valuation.circulating_market_cap, #流通市值
            balance.fixed_assets / balance.total_assets, #固定资产和总资产比值
            #盈利因子
            indicator.net_profit_to_total_revenue, #净利润/营业总收入
            indicator.gross_profit_margin, #销售毛利率GPM
            indicator.roe, #净资产回报率
            indicator.roa, #资产回报率
            income.operating_profit / income.total_profit, #主营业务占比
            #成长因子
            indicator.inc_revenue_year_on_year,  #营业收入增长率（同比）
            indicator.inc_net_profit_year_on_year,#净利润增长率（同比）
            ).filter(
                valuation.code.in_(feasible_stocks)
            )
        return get_fundamentals(q, current_date)
    '''获取因子训练集'''
    def get_train_Factor(self, feasible_stocks, current_date, delta, term):
        factor_data = get_init_Factor(feasible_stocks, current_date)
        for i in range(term):
            factor_date = tools.shift_trading_day(current_date, delta * (i + 1))
            factor = get_init_Factor(feasible_stocks, factor_date)
            factor_data = pd.concat([factor_data, factor], ignore_index = True)
        #factor_process(factor_data)
        return factor_data
    '''因子数据处理'''
    def factor_process(self, factor_df):
        df = pd.DataFrame()
        #df['code'] = factor_df['code']
        df['log_market_cap'] = np.log(factor_df['market_cap']) #标签：对数市值 
        '''估值因子'''
        df['EP'] = factor_df['pe_ratio'].apply(lambda x: 1/x) #估值因子：EP 市赢率的倒数
        df['BP'] = factor_df['pb_ratio'].apply(lambda x: 1/x) #估值因子：BP 市净率的倒数
        df['PS'] = factor_df['ps_ratio'] #估值因子：PS市销率
        df['RD'] = factor_df['development_expenditure']/(factor_df['market_cap'] * 100000000) #估值因子：RP，市研率
        df['DP'] = factor_df['dividend_payable'] / (factor_df['market_cap'] * 100000000) #估值因子：DP，股息率
        '''资本结构因子'''
        df['log_net_equity'] = np.log(factor_df['anon_1']) #资本结构因子:log_net_equity-净资产的对数
        df['LEV'] = factor_df['anon_2'] #资本结构因子:lev-财务杠杆
        df['log_circulating_market_cap'] = np.log(factor_df['circulating_market_cap']) #资本结构因子:流动市值的对数
        df['fix_asset'] = factor_df['anon_3'] #资本结构因子:固定资产比上总资产 data['one'].apply(lambda x: 0 if x < 0 else x)
        '''收益因子'''
        df['NI_rate_gain'] = factor_df['net_profit_to_total_revenue'].apply(lambda x: 0 if x < 0 else x) #收益因子-正的净利润率
        df['NI_rate_loss'] = factor_df['net_profit_to_total_revenue'].apply(lambda x: 0 if x > 0 else np.abs(x)) #收益因子-负的净利润率
        df['gross_profit_margin'] = factor_df['gross_profit_margin'] #收益因子-销售毛利率
        df['ROE'] = factor_df['roe'] #收益因子-净资产收益率
        df['ROA'] = factor_df['roa'] #收益因子-资产收益率
        df['OPTP'] = factor_df['anon_4'] #收益因子-营收占收入比
        '''成长因子'''
        df['g'] = factor_df['inc_revenue_year_on_year'] #成长因子-营收增长率
        df['NI_g'] = factor_df['inc_net_profit_year_on_year'] #成长因子-净利润增长率
        df['PEG'] = factor_df['pe_ratio'] / (df['NI_g'] * 100) #成长因子-PEG
        df = df.fillna(0)    
        return d
    '''因子数据清洗'''
    def factor_wash(self, factor_data):
        #tools.replace_nan_indu(factor_data, stockList, industry_code, date)
        factor_data = winsorize_med(factor_data, scale=5, inclusive=True, inf2nan=True, axis=0)
        factor_data = tools.standardize_df(factor_data)
        factor_data = tools.neutralize_df(factor_data, exclude = 'log_market_cap', industry=True)
        return factor_data
    
    '''                         策略逻辑部分                                     '''
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
            
    def set_stragy_param(self):
        self.learn_algorithm = 'svr' #机器学习算法
        self.group_quantile = 0.1 #分组颗粒度
        self.group_num = 1 #组号
        self.group_num = 1 #组号
        self.trade_day = 0 #交易日
        self.trade_step = 10 #交易步长
        self.trade_flag = False #调仓交易标志
        self.Modle = None #模型
        
    
    def initialize(self, context):
        set_stragy_param();
        #set_slippage(FixedSlippage(0)) #设置滑点
                
    def before_trading(self, context):        
        #setCommission() #设置手续费
        if self.trade_day % self.trade_step == 0:
            self.trade_flag = True
            current_dt = context.current_dt
            current_date = current_dt.strftime('%Y-%m-%d')        
            yesterday = tools.shift_trading_day(current_date, 1)
            stock_list = get_index_stocks(index_Code)
            feasible_stocks = get_nopaued_stock(stock_list, current_date)
            train_factor = get_train_Factor(feasible_stocks, yesterday, 60, 4)
            test_factor = get_init_Factor(stock_list, current_date)
            train_factor_process = factor_process(train_factor)
            train_factor_wash = factor_wash(train_factor_process)
            test_factor_process = factor_process(test_factor)
            test_factor_wash = factor_wash(test_factor_process)
            y_train = train_factor_wash['log_market_cap']
            X_train = train_factor_wash.drop('log_market_cap',axis = 1)
            y_test = test_factor_wash[['log_market_cap']]
            X_test = test_factor_wash.drop('log_market_cap',axis = 1)
            kfold = KFold(n_splits=4)
            if self.learn_algorithm == 'svr':
                para_grid = {'C':[5,100],'gamma':[0,1,10]}
                grid_search_model = SVR()
            elif self.learn_algorithm == 'lr':    
                grid_search_model = LinearRegression()
            elif self.learn_algorithm == 'ridge':    
                para_grid = {'alpha':[1,10,100]}
                grid_search_model = Ridge()
            elif self.learn_algorithm == 'rf':    
                para_grid = {'n_estimators':[100,500,1000]}
                grid_search_model = RandomForestRegressor()
            else:
                g.__scoreWrite = False
            model = GridSearchCV(grid_search_model, para_grid, cv=kfold, n_jobs = -1)
            model.fit(X_train, y_train) #学习训练集数据，并由KFold将训练集化为训练集和验证集，
            model = model.best_estimator_ #选择最好的参数，组成预测模型      
        
    def handle(self, context):
        
        if self.trade_flag:     
            y_pred = model.predict(X_test) # 预测值     
            factor = y_test - pd.DataFrame(y_pred, index = test_factor.code, columns = ['log_market_cap'])  # 新的因子：实际值与预测值之差  
            factor = factor.sort_values(by = 'log_market_cap', ascending = False)  #对新的因子，即残差进行排序（按照从小到大）

            group_count = int(self.group_quantile * len(factor))
            group_list = []
            for i in range(int(1.0/group_quantile)):
                start = i * group_count
                end = (i + 1) * group_count
                group_list.append(stock_list[start:end])

            holdstock = list(self.self.context.portfolio.positions.keys())  # 获取持仓股票
            logger.info('日期{}持仓股票:{}'.format(cunrrent_date, holdstock))
            buy_stock = list(set(holdstock).difference(set(group_list[0])))
            for s in holdstock:
                if s not in group_list[0]:
                    self.order_target(s, 0)
            for s in buy_stock
                self.order(s, self.context.portfolio.available_cash / len(buy_stock))
    
    def after_trading(self, context):
        self.trade_day += 1
        
        
