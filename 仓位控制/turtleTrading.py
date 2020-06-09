'''海龟交易系统'''
class turtleTrading():
    
    def __init__(self, N_step = 20):
        self.tqa_high = []
        self.tqa_middle = []
        self.tqa_low = []
        self.N_compute = []
        self.N_step = N_step #默认10
        
    def compute_volatility_N(data = None):
        if not data:
            print('未发现待处理数据！')
            return None  
        hign_close_max = data['high'] - data['low']
        high_closepre_max = abs(data['high'] - data['close'].shift(1).fillna(0))#绝对值
        low_closepre_max = abs(data['low'] - data['close'].shift(1).fillna(0))#绝对值
        middle_state = tools.compare_serice(hign_close_max[1:], high_closepre_max[1:], 'max')
        volatility_range = tools.compare_serice(middle_state, low_closepre_max[1:], 'max')
        return volatility_range
        
    def get_volatility_N(data = None):
        if not data:
            print('未发现待处理数据！')
            return None
        if len(N_compute) == 0:    
            volatility_range = compute_volatility_N(data)
            self.N_compute.append(volatility_range) 
        else:
            volatility_range = compute_volatility_N(data)
            #N=Rolling((PreN∗19+TrueRange20) / 20)
            volatility_range_weight = (N_compute[-1]*(self.N_step-1) + volatility_range*(self.N_step)) / self.N_step
            self.N_compute.append(volatility_range_weight.rolling(window = 2,min_periods = 1).mean())#移动平均
            
    def get_tqa_line(data = None):

        if not data:
            print('未发现待处理数据！')
            return None
        self.tqa_high.append(max(data['high']))
        self.tqa_low.append(min(data['low']))
        self.tqa_middle.append(((max(data['high']) + min(data['low']))/2.0))
