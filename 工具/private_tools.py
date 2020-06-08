import datetime
import pandas as pd
import numpy as np
from jqdata import *
class private_tools():
    '''比较DataFrame'''
    def compare_serice(self, serice_1, serice_2, flag):
        if flag == 'max':
            compare_flag = (serice_1 > serice_2)
            serice_2[compare_flag] = serice_1[compare_flag]
            return serice_2
        if flag == 'min':
            compare_flag = (serice_1 < serice_2)
            serice_2[compare_flag] = serice_1[compare_flag]
            return serice_2
    '''利用采样函数，设定转换周期period_type  转换为周是'W',月'M',季度线'Q',五分钟'5min',12天'12D''''
    def get_period_date(peroid,start_date, end_date):
        stock_data = get_price('000001.XSHE',start_date,end_date,'daily',fields=['close'])
        #types = stock_data.index.dtype 查看index的数据类型
        stock_data['date']=stock_data.index #resample按照index自然日采样，获取日期临时值
        start_date_0 = stock_data['date'][0].strftime("%Y-%m-%d")
        period_stock_data=stock_data.resample(peroid,how= 'last').dropna() #进行转换，周线的每个变量都等于那一周中最后一个交易日的变量值
        date_list = period_stock_data['date'].apply(lambda s: s.strftime('%Y-%m-%d')).values.tolist() #numpy.arrange 转 list
        date_list.insert(0, start_date_0)
        return date_list
    '''过滤次新股票'''
    def filter_new_stock(stocks, currernt_date, delta = 30 * 6):
        stockList=[]
        currernt_date = datetime.datetime.strptime(currernt_date, "%Y-%m-%d")
        for stock in stocks:
            start_date = get_security_info(stock).start_date
            if start_date < (currernt_date - datetime.timedelta(days = delta)).date():
                stockList.append(stock)
        return stockList
    '''获取股票池'''
    def filter_st_stock(stocks, current_date):
        #剔除ST股
        st_stock_info = get_extras('is_st', stocks, count = 1, end_date = current_date)
        stock_filter = [stock for stock in stocks if not st_stock_info[stock][0]]
        return stock_filter
    '''数据清洗函数工具'''
    '''
    mad中位数去极值法
    series:待处理数据，Series
    n：几个单位的偏离值
    '''
    def filter_extreme_MAD(series_pre, n):
        median = series_pre.quantile(0.5)
        new_median = ((series_pre - median).abs()).quantile(0.50)
        max_range = median + n * new_median
        min_range = median - n * new_median
        return np.clip(series_pre, min_range, max_range)

    '''
    方差取极值
    series_pre:待处理数据，数据类型Series
    std:为几倍的标准差，
    have_negative 为布尔值，是否包括负值
    '''
    def filter_extreme_std(series_pre, n=3, have_negative=True):

        series_pre_copy = series_pre.dropna().copy()
        if have_negative == False:
            series_pre_copy = series_pre_copy[series_pre_copy >= 0]
        else:
            pass
        edge_up = series_pre_copy.mean() + n * series_pre_copy.std()
        edge_low = series_pre_copy.mean() - n * series_pre_copy.std()
        series_pre_copy[series_pre_copy > edge_up] = edge_up
        series_pre_copy[series_pre_copy < edge_low] = edge_low
        return series_pre_copy
    '''
    标准化函数：
    series_pre:待处理数据，数据类型Series
    ty：标准化类型:1 MinMax,2 Standard,3 maxabs
    '''
    def standardize(series_pre, ty = 2):
        series_pre_copy = series_pre.dropna().copy()
        if int(ty) == 1:
            series_pre_copy = (series_pre_copy - series_pre_copy.min()) / (series_pre_copy.max() - series_pre_copy.min())
        elif ty == 2:
            std = series_pre_copy.std()
            if std == 0:
                std = 1
            re = (series_pre_copy - series_pre_copy.mean()) / std
        elif ty == 3:
            re = series_pre_copy / (10 ** np.ceil(np.log10(series_pre_copy.abs().max())))
        return re
    '''
    缺失值处理，一般情况应该去除drop（how = ‘any’）,但A股数据量本来缺少，最终还是决定以均值替代
    若是行业中因子值为空，则以所有行业均值代替
    某只股票因子值为空，用行业平均值代替，
    依然会有nan，则用所有股票平均值代替
    ''' 
    def replace_nan_indu(factor_data, stockList, industry_code, date):

        i_Constituent_Stocks = {}
        if isinstance(factor_data, pd.DataFrame):
            data_temp = pd.DataFrame(index=industry_code, columns=factor_data.columns)
            for i in industry_code:
                temp = get_industry_stocks(i, date)
                i_Constituent_Stocks[i] = list(set(temp).intersection(set(stockList)))
                data_temp.loc[i] = np.mean(factor_data.loc[i_Constituent_Stocks[i], :])
            for factor in data_temp.columns:
                # 行业缺失值用所有行业平均值代替
                null_industry = list(data_temp.loc[pd.isnull(data_temp[factor]), factor].keys())
                for i in null_industry:
                    data_temp.loc[i, factor] = np.mean(data_temp[factor])
                null_stock = list(factor_data.loc[pd.isnull(factor_data[factor]), factor].keys())
                for i in null_stock:
                    industry = get_key(i_Constituent_Stocks, i)
                    if industry:
                        factor_data.loc[i, factor] = data_temp.loc[industry[0], factor]
                    else:
                        factor_data.loc[i, factor] = np.mean(factor_data[factor])
        return factor_data
    '''
    中性化函数，对需要待中性化的因子进行中性化回归，其残差即为中性化后的因子值
    输入：
    mkt_cap：以股票为index，市值为value的Series,
    factor：以股票code为index，因子值为value的Series,
    输出：
    中性化后的因子值series
    ''' 
    def neutralization(factor, mkt_cap=False, industry=False):
        y = factor
        if type(mkt_cap) == pd.Series:
            # LnMktCap = mkt_cap.apply(lambda x:math.log(x))
            if industry:  # 行业、市值
                dummy_industry = get_industry_exposure(factor.index)
                x = pd.concat([mkt_cap, dummy_industry.T], axis=1)
            else:  # 仅市值
                x = mkt_cap
        elif industry:  # 仅行业
            dummy_industry = get_industry_exposure(factor.index)
            x = dummy_industry.T
        result = sm.OLS(y.astype(float), x.astype(float)).fit()
        return result.resid

    '''为股票池添加行业标记'''
    def get_industry_exposure(stock_list):
        df = pd.DataFrame(index = (get_industries(name='sw_l1').index), columns=stock_list)
        for stock in stock_list:
            try:
                df[get_industry_code_from_security(stock)][stock] = 1
            except:
                continue
        return df.fillna(0)  # 将NaN赋为0

    '''查询个股所在行业函数代码（申万一级） ,为中性化函数的子函数'''
    def get_industry_code_from_security(security, date=None):
        industry_index = get_industries(name='sw_l1').index
        for i in range(0, len(industry_index)):
            try:
                index = get_industry_stocks(industry_index[i], date=date).index(security)
                return industry_index[i]
            except:
                continue
        return u'未找到'
    
