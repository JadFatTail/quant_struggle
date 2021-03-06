from jqdata import *
from jqlib.technical_analysis import *
from jqfactor import get_factor_values
from jqfactor import winsorize_med
from jqfactor import standardlize
from jqfactor import neutralize
import datetime
import pandas as pd
import numpy as np
from . import stragy_turtleTrade

tools = private_tools()
#数据预处理
def factor_wash(factor_data, stockList, industry_code, date):
    #去极值，目前private_tools支持单series的去极值化处理，待完成dataframe级别后替代
    factor_data = winsorize_med(factor_data, scale=5, inf2nan=False,axis=0)
    #缺失值处理，目前已完成private_tools支持
    factor_data = tools.replace_nan_indu(factor_data,stockList,industry_code,date)
    #中性化处理，目前已完成private_tools支持
    factor_data = neutralize(factor_data, mkt_cap=False, industry=False)
    #标准化处理,目前private_tools支持单series的去极值化处理，待完成dataframe级别后替代
    factor_data = standardlize(factor_data,axis=0)
