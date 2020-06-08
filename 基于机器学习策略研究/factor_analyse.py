from jqdata import *
from jqlib.technical_analysis import * #后续迭代成talib中的方法
from jqfactor import get_factor_values #后续迭代成private_tools中的方法
from jqfactor import winsorize_med #后续迭代成private_tools中的方法
from jqfactor import standardlize #后续迭代成private_tools中的方法
from jqfactor import neutralize #后续迭代成private_tools中的方法
import datetime
import pandas as pd
import numpy as np
def factor_analyse(current_date = '2019-05-25', stock_list = ['000728.XSHE', '000725.XSHE']):
    df = pd.DataFrame()
    data = pd.DataFrame()
    try:
        q = query(valuation, balance, cash_flow, income, indicator).filter(valuation.code.in_(stock_list))
        df = get_fundamentals(q, current_date)
    except Error as e:
        log.info('获取财务数据发升异常')
    df['market_cap'] = df['market_cap'] * 100000000
    #factor_data:{factor:df};
    factor_data = get_factor_values(stock_list, ['roe_ttm',
                                             'roa_ttm',
                                             'total_asset_turnover_rate',
                                             'net_operate_cash_flow_ttm',
                                             'net_profit_ttm',
                                             'cash_to_current_liability',
                                             'current_ratio',
                                             'gross_income_ratio',
                                             'non_recurring_gain_loss',
                                             'operating_revenue_ttm',
                                             'net_profit_growth_rate'
                                            ], end_date = current_date, count=1)
    factor_df = pd.DataFrame(index = stock_list)
    for i in factor_data.keys():
        factor_df[i] = factor_data[i].iloc[0,:]
    factor_df.head()
    df.index = df['code']
    del df['code'], df['id']
    '''
    df：index为stock
    factor_df:index为stock
    '''
    df = pd.concat([df, factor_df], axis=1) #合并得大表,横向合并
    data['EP']=df['net_profit_ttm']/df['market_cap']
    #净资产/总市值
    data['BP']=1/df['pb_ratio']
    #营业收入(TTM)/总市值
    data['SP']=1/df['ps_ratio']
    #净现金流(TTM)/总市值
    data['NCFP']=1/df['pcf_ratio']
    #经营性现金流(TTM)/总市值
    data['OCFP']=df['net_operate_cash_flow_ttm']/df['market_cap']
    #净利润(TTM)同比增长率/PE_TTM
    data['G/PE']=df['net_profit_growth_rate']/df['pe_ratio']
    #ROE_ttm
    data['roe_ttm']=df['roe_ttm']
    #ROE_YTD
    data['roe_q']=df['roe']
    #ROA_ttm
    data['roa_ttm']=df['roa_ttm']
    #ROA_YTD
    data['roa_q']=df['roa']
    #毛利率TTM
    data['grossprofitmargin_ttm']=df['gross_income_ratio']
    #毛利率YTD
    data['grossprofitmargin_q']=df['gross_profit_margin']

    #扣除非经常性损益后净利润率YTD
    data['profitmargin_q']=df['adjusted_profit']/df['operating_revenue']
    #资产周转率TTM
    data['assetturnover_ttm']=df['total_asset_turnover_rate']
    #资产周转率YTD 营业收入/总资产
    data['assetturnover_q']=df['operating_revenue']/df['total_assets']
    #经营性现金流/净利润TTM
    data['operationcashflowratio_ttm']=df['net_operate_cash_flow_ttm']/df['net_profit_ttm']
    #经营性现金流/净利润YTD
    data['operationcashflowratio_q']=df['net_operate_cash_flow']/df['net_profit']
    #净资产
    df['net_assets']=df['total_assets']-df['total_liability']
    #总资产/净资产
    data['financial_leverage']=df['total_assets']/df['net_assets']
    #非流动负债/净资产
    data['debtequityratio']=df['total_non_current_liability']/df['net_assets']
    #现金比率=(货币资金+有价证券)÷流动负债
    data['cashratio']=df['cash_to_current_liability']
    #流动比率=流动资产/流动负债*100%
    data['currentratio']=df['current_ratio']
    #总市值取对数
    data['ln_capital']=np.log(df['market_cap'])
     #TTM所需时间
    his_date = [pd.to_datetime(current_date) - datetime.timedelta(90*i) for i in range(0, 4)] #过去四个季度
    tmp = pd.DataFrame()
    tmp['code'] = stock_list
    for i in his_date:
        tmp_adjusted_dividend = get_fundamentals(query(indicator.code, indicator.adjusted_profit, \
                                                     cash_flow.dividend_interest_payment).
                                               filter(indicator.code.in_(stock_list)), date = i)
        tmp=pd.merge(tmp, tmp_adjusted_dividend, how='outer', on='code')

        tmp=tmp.rename(columns={'adjusted_profit':'adjusted_profit' + str(i.month), \
                                'dividend_interest_payment':'dividend_interest_payment' + str(i.month)})
    tmp=tmp.set_index('code')
    tmp_columns=tmp.columns.values.tolist()
    tmp_adjusted=sum(tmp[[i for i in tmp_columns if 'adjusted_profit'in i ]], axis = 1) #列加和
    tmp_dividend=sum(tmp[[i for i in tmp_columns if 'dividend_interest_payment'in i ]], axis = 1) #列加和
    #扣除非经常性损益后净利润(TTM)/总市值
    data['EPcut']=tmp_adjusted/df['market_cap']
    #近12个月现金红利(按除息日计)/总市值
    data['DP']=tmp_dividend/df['market_cap']
    #扣除非经常性损益后净利润率TTM
    data['profitmargin_ttm']=tmp_adjusted/df['operating_revenue_ttm']
    #营业收入(YTD)同比增长率
    #_x现在 _y前一年
    his_date = pd.to_datetime(current_date) - datetime.timedelta(365)
    name = ['operating_revenue','net_profit','net_operate_cash_flow','roe']
    temp_data = df[name]
    his_temp_data = get_fundamentals(query(valuation.code, income.operating_revenue,income.net_profit,\
                                            cash_flow.net_operate_cash_flow,indicator.roe).
                                      filter(valuation.code.in_(stock_list)), date = his_date)
    his_temp_data = his_temp_data.set_index('code')
    for i in name:
        his_temp_data=his_temp_data.rename(columns={i:i+'last_year'})
    temp_data =pd.concat([temp_data,his_temp_data],axis=1)
    #营业收入(YTD)同比增长率
    data['sales_g_q']=temp_data['operating_revenue']/temp_data['operating_revenuelast_year']-1
    #净利润(YTD)同比增长率
    data['profit_g_q']=temp_data['net_profit']/temp_data['net_profitlast_year']-1
    #经营性现金流(YTD)同比增长率
    data['ocf_g_q']=temp_data['net_operate_cash_flow']/temp_data['net_operate_cash_flowlast_year']-1
    #ROE(YTD)同比增长率
    data['roe_g_q']=temp_data['roe']/temp_data['roelast_year']-1
    #个股60个月收益与上证综指回归的截距项与BETA
    stock_close=get_price(stock_list, count = 60*20+1, end_date = current_date, frequency='daily', fields=['close'])['close']
    SZ_close=get_price('000001.XSHG', count = 60*20+1, end_date = current_date, frequency='daily', fields=['close'])['close']
    stock_pchg=stock_close.pct_change().iloc[1:]
    SZ_pchg=SZ_close.pct_change().iloc[1:]
    beta=[]
    stockalpha=[]
    for i in stock_list:
        temp_beta, temp_stockalpha = stats.linregress(SZ_pchg, stock_pchg[i])[:2]
        beta.append(temp_beta)
        stockalpha.append(temp_stockalpha)
    #此处alpha beta为list
    data['alpha']=stockalpha
    data['beta']=beta
    #动量
    data['return_1m']=stock_close.iloc[-1]/stock_close.iloc[-20]-1
    data['return_3m']=stock_close.iloc[-1]/stock_close.iloc[-60]-1
    data['return_6m']=stock_close.iloc[-1]/stock_close.iloc[-120]-1
    data['return_12m']=stock_close.iloc[-1]/stock_close.iloc[-240]-1
    #取换手率数据
    data_turnover_ratio=pd.DataFrame()
    data_turnover_ratio['code'] = stock_list
    trade_days=list(get_trade_days(end_date = current_date, count=240*2))
    for i in trade_days:
        q = query(valuation.code, valuation.turnover_ratio).filter(valuation.code.in_(stock_list))
        temp = get_fundamentals(q, i)
        data_turnover_ratio = pd.merge(data_turnover_ratio, temp, how='left',on='code')
        data_turnover_ratio = data_turnover_ratio.rename(columns={'turnover_ratio':i})
    data_turnover_ratio = data_turnover_ratio.set_index('code').T   
    #个股个股最近N个月内用每日换手率乘以每日收益率求算术平均值
    data['wgt_return_1m'] = mean(stock_pchg.iloc[-20:]*data_turnover_ratio.iloc[-20:])
    data['wgt_return_3m'] = mean(stock_pchg.iloc[-60:]*data_turnover_ratio.iloc[-60:])
    data['wgt_return_6m'] = mean(stock_pchg.iloc[-120:]*data_turnover_ratio.iloc[-120:])
    data['wgt_return_12m'] = mean(stock_pchg.iloc[-240:]*data_turnover_ratio.iloc[-240:])
    #个股个股最近N个月内用每日换手率乘以函数exp(-x_i/N/4)再乘以每日收益率求算术平均值
    temp_data = pd.DataFrame(index=data_turnover_ratio[-240:].index, columns = stock_list)
    temp=[]
    for i in range(240):
        if i/20< 1:
            temp.append(exp(-i/1/4))
        elif i/20< 3:
            temp.append(exp(-i/3/4))
        elif i/20< 6:
            temp.append(exp(-i/6/4))
        elif i/20< 12:
            temp.append(exp(-i/12/4))  
    temp.reverse()
    for i in stock_list:
        temp_data[i]=temp
    data['exp_wgt_return_1m']=mean(stock_pchg.iloc[-20:]*temp_data.iloc[-20:]*data_turnover_ratio.iloc[-20:])
    data['exp_wgt_return_3m']=mean(stock_pchg.iloc[-60:]*temp_data.iloc[-60:]*data_turnover_ratio.iloc[-60:])
    data['exp_wgt_return_6m']=mean(stock_pchg.iloc[-120:]*temp_data.iloc[-120:]*data_turnover_ratio.iloc[-120:])
    data['exp_wgt_return_12m']=mean(stock_pchg.iloc[-240:]*temp_data.iloc[-240:]*data_turnover_ratio.iloc[-240:])
    #特异波动率
    #获取FF三因子残差数据
    '''
    LoS = len(stock_list)
    S = df.sort_values(by = 'market_cap')[:int(LoS/3)].index 
    B = df.sort_values(by = 'market_cap')[int(LoS-LoS/3):].index

    df['BTM'] = df['total_owner_equities']/df['market_cap']
    L = df.sort_values(by = 'BTM')[:int(LoS/3)].index
    H = df.sort_values(by = 'BTM')[int(LoS-LoS/3):].index
    df_temp = stock_pchg.iloc[-240:]
    #求因子的值
    SMB = sum(df_temp[S].T)/len(S)-sum(df_temp[B].T)/len(B)
    HMI = sum(df_temp[H].T)/len(H)-sum(df_temp[L].T)/len(L)
    #用中证800作为大盘基准
    dp = get_price('000300.XSHG',count=12*20+1,end_date=date,frequency='daily', fields=['close'])['close']
    RM = dp.pct_change().iloc[1:]-0.04/252
    #将因子们计算好并且放好
    X = pd.DataFrame({"RM":RM,"SMB":SMB,"HMI":HMI})
    resd = pd.DataFrame()
    for i in stock:
        temp=df_temp[i]-0.04/252
        t_r=linreg(X,temp)
        resd[i]=list(temp-(t_r[0]+X.iloc[:,0]*t_r[1]+X.iloc[:,1]*t_r[2]+X.iloc[:,2]*t_r[3]))
    data['std_FF3factor_1m'] = resd[-1*20:].std()
    data['std_FF3factor_3m'] = resd[-3*20:].std()
    data['std_FF3factor_6m'] = resd[-6*20:].std()
    data['std_FF3factor_12m'] = resd[-12*20:].std()
    '''
    #波动率
    data['std_1m']=stock_pchg.iloc[-20:].std()
    data['std_3m']=stock_pchg.iloc[-60:].std()
    data['std_6m']=stock_pchg.iloc[-120:].std()
    data['std_12m']=stock_pchg.iloc[-240:].std()

    #股价
    data['ln_price']=np.log(stock_close.iloc[-1])

    #换手率
    data['turn_1m']=mean(data_turnover_ratio.iloc[-20:])
    data['turn_3m']=mean(data_turnover_ratio.iloc[-60:])
    data['turn_6m']=mean(data_turnover_ratio.iloc[-120:])
    data['turn_12m']=mean(data_turnover_ratio.iloc[-240:])

    data['bias_turn_1m']=mean(data_turnover_ratio.iloc[-20:])/mean(data_turnover_ratio)-1
    data['bias_turn_3m']=mean(data_turnover_ratio.iloc[-60:])/mean(data_turnover_ratio)-1
    data['bias_turn_6m']=mean(data_turnover_ratio.iloc[-120:])/mean(data_turnover_ratio)-1
    data['bias_turn_12m']=mean(data_turnover_ratio.iloc[-240:])/mean(data_turnover_ratio)-1
    #技术指标
    data['PSY']=pd.Series(PSY(stock_list, current_date, timeperiod=20))
    data['RSI']=pd.Series(RSI(stock_list, current_date, N1=20))
    data['BIAS']=pd.Series(BIAS(stock_list, current_date, N1=20)[0])
    dif, dea, macd=MACD(stock_list, current_date, SHORT = 10, LONG = 30, MID = 15)
    data['DIF']=pd.Series(dif)
    data['DEA']=pd.Series(dea)
    data['MACD']=pd.Series(macd)
    return data
