

# # 1. SmartApi CALL

import SmartApi
from SmartApi.smartConnect import SmartConnect
from SmartApi import smartWebSocketV2
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import SmartApi.smartExceptions
import os
from logzero import logger
from pyotp import TOTP
import urllib
import urllib.request
import json
import pandas as pd
import numpy as np
import datetime as dt
import time
import os
import stockstats
from stockstats import StockDataFrame
import pandas_ta as ta
import winsound 
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('--api_key', dest='api_key', type=str, help='Add api_key')
parser.add_argument('--api_secret', dest='api_secret', type=str, help='Add api_secret')
parser.add_argument('--client_code', dest='client_code', type=str, help='Add client_code')
parser.add_argument('--mpin', dest='mpin', type=str, help='Add mpin')
parser.add_argument('--totp_code', dest='totp_code', type=str, help='Add totp_code')

args = parser.parse_args()






# key_path=r'C:\Users\Administrator\Downloads\AngelOne'
# os.chdir(key_path)
# key_secret   = open('angelone_login.txt', 'r').read().split()    #api_key, api_secret, user_id, mpin, totp_code
time.sleep(0.5)
[api_key, api_secret, client_code, mpin, totp_code]= [args.api_key, args.api_secret, args.client_code, args.mpin, args.totp_code]
totp         = TOTP(totp_code).now()
smart        = SmartConnect(api_key=api_key)
data         = smart.generateSession(client_code, mpin, totp)

refreshToken = data['data']['refreshToken']
auth_token   = data['data']['jwtToken']
feed_token   = smart.getfeedToken()
userProfile  = smart.getProfile(refreshToken)
sws          = SmartWebSocketV2(auth_token, api_key, client_code, feed_token, max_retry_attempt=1)
print(pd.DataFrame(userProfile))


# # 2. GLOBAL FUNCTIONS

# ## 2.1 DAILY INSTRUMENTS LIST


instrument_url  = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json'
response        = urllib.request.urlopen(instrument_url)
instrument_list = json.loads(response.read())
time.sleep(0.3)


NIFTY50 = ['POWERGRID', 'TITAN', 'HDFCLIFE', 'M&M', 'BPCL', 'NTPC', 'BRITANNIA', 'HEROMOTOCO', 'BAJAJFINSV', 'TATAMOTORS', 'BAJAJ-AUTO', 'ITC', 
           'NESTLEIND', 'SBIN', 'CIPLA', 'HINDUNILVR', 'COALINDIA', 'BAJFINANCE', 'LT', 'ASIANPAINT', 'TATACONSUM', 'INDUSINDBK', 'TCS', 'SBILIFE', 'ONGC', 
           'SUNPHARMA', 'HCLTECH', 'EICHERMOT', 'APOLLOHOSP', 'MARUTI', 'ICICIBANK', 'AXISBANK', 'JSWSTEEL', 'LTIM', 'TECHM', 'KOTAKBANK', 'RELIANCE', 
           'GRASIM', 'UPL', 'DIVISLAB', 'TATASTEEL', 'WIPRO', 'ULTRACEMCO', 'INFY', 'ADANIENT', 'BHARTIARTL', 'DRREDDY', 'ADANIPORTS', 'HDFCBANK', 'HINDALCO']


options           = pd.DataFrame(instrument_list)
options           = options[((options['exch_seg']=='NFO') | (options['exch_seg']=='BFO')) & (options['instrumenttype']=='OPTIDX')]
options['expiry'] = pd.to_datetime(options['expiry'], format='%d%b%Y')
options['strike'] = (options['strike'].astype(float))/100
options.sort_values(by='expiry', inplace=True)
options.reset_index(drop=True, inplace=True)

futures           = pd.DataFrame(instrument_list)
futures           = futures[(futures['instrumenttype']=='FUTIDX') | (futures['instrumenttype']=='FUTSTK')]
futures['expiry'] = pd.to_datetime(futures['expiry'], format='%d%b%Y')
futures.sort_values(by='expiry', inplace=True)
futures.reset_index(drop=True, inplace=True)


# ## 2.2 GLOBAL FUNCTIONS
# https://smartapi.angelbroking.com/docs/RateLimit

def get_token(symbol, instrument_list, exchange='NSE'):
    if (symbol[-2:] in ['CE', 'PE']) or (symbol[-3:] =='FUT') & (exchange!='MCX'): exchange='NFO' 
    for instrument in instrument_list:
        if instrument['symbol']==symbol and instrument['exch_seg']==exchange:
            return instrument['token']

def get_symbol(ticker, instrument_list, exchange='NSE'):
    for instrument in instrument_list:
        if instrument['name']==ticker and instrument['exch_seg']==exchange and instrument['symbol'].split('-')[-1]=='EQ':
            return instrument['symbol']

def get_optn_token(option_symbol, options):
    option_data = options[options['symbol']==option_symbol]
    return option_data['token'].iloc[0]
        
def get_optn_symbol(options, index=None, strike_price=None, call_put=None, expiry=None):
    if   index in ['BANKNIFTY', 'bnf', 'BNF','banknifty']:  index= 'BANKNIFTY'
    elif index in ['FINNIFTY', 'fin', 'FIN', 'finnnifty']:  index= 'FINNIFTY'
    elif index in ['NIFTY', 'nifty', 'nif', 'NIF'       ]:  index= 'NIFTY'
    elif index in ['SENSEX', 'sensex','sen', 'SEN'      ]:  index= 'SENSEX'
    elif index in ['BANKEX', 'bankex'                   ]:  index= 'BANKEX'
    call_put='CE' if call_put in ['call', 'CALL', 'ce', 'CE', 'c', 'C'] else 'PE' 
    
    options = options[(options['name'] == index) & (options['strike']==strike_price)]
    options.reset_index(drop=True, inplace=True)
    options=options[options['expiry']==options['expiry'].loc[0]] if expiry==None else options[options['expiry']==expiry]
    return options['symbol'][0] if (call_put in options['symbol'][0]) else options['symbol'][1]

def get_fut_symbol(name, futures):
    return futures[(futures['name']==name)]['symbol'].iloc[0]

def get_fut_token(symbol, futures):
    return futures[futures['symbol']==symbol]['token'].iloc[0]
    
def get_ltp(symbol, exchange='NSE'):  
    if ('0CE' in symbol) or ('0PE' in symbol): 
        [symbol_token, exchange]=[get_optn_token(symbol, options), 'NFO' if ('SENSEX' not in symbol) and ('BANKEX' not in symbol) else 'BFO']
    elif exchange=='MCX': [symbol_token, exchange]=[get_token(symbol, instrument_list, 'MCX'), 'MCX']
    elif 'FUT' in symbol: [symbol_token, exchange]=[get_fut_token(symbol, futures), 'NFO']
    else: [symbol_token, exchange]=[get_token(symbol, instrument_list), exchange]
    return smart.ltpData(exchange=exchange,tradingsymbol=symbol,symboltoken=symbol_token)['data']['ltp']
    
def positions():
    Positions=pd.DataFrame(smart.position()['data'])
    if(Positions.empty==False):
        Positions        = Positions[['symboltoken', 'symbolname', 'instrumenttype', 'tradingsymbol', 'netqty', 'buyavgprice', 
                                      'sellavgprice', 'pnl', 'realised', 'unrealised', 'ltp', 'producttype', 'exchange']]
        
        Positions[['netqty','buyavgprice', 'sellavgprice', 'pnl', 'realised', 'unrealised', 'ltp']] \
        = Positions[['netqty','buyavgprice', 'sellavgprice', 'pnl', 'realised', 'unrealised', 'ltp']].astype(float)

        Positions.loc[len(Positions.index)] = ['TOTAL','' ,'' ,'' , '', '','' , Positions['pnl'].sum(),'','','','','']
        return Positions
    else:
        return pd.DataFrame(columns=['symboltoken', 'symbolname', 'instrumenttype', 'tradingsymbol', 'netqty', 
                             'buyavgprice', 'sellavgprice', 'pnl', 'realised', 'unrealised', 'ltp', 'producttype', 'exchange'])        
def net_pnl():
    Positions= positions()
    return Positions['pnl'].iloc[-1] if (not Positions['pnl'].empty) else 0

def daily_return():
    bod_funds=float(smart.rmsLimit()['data']['net'])
    Net_pnl=net_pnl()
    return round((Net_pnl/bod_funds)*100,1)    
       
def holdings():
    Holdings= pd.DataFrame(smart.holding()['data'])
    if len(Holdings)!=0 : return Holdings.drop(columns=['isin','t1quantity', 'realisedquantity','authorisedquantity']) 
    else                : return 0
    
def inst_time():
    return dt.datetime.now().strftime('%I:%M:%S')

def print_bold(text):
    print("\033[1m" + text + "\033[0m")   
    
def alert(n=1):
    for i in range(n): winsound.Beep(1000,500)

# ## 2.3 GLOBAL ORDER TYPES

#     variety=['NORMAL','AMO','STOPLOSS','ROBO'], ordertype=['MARKET','LIMIT','STOPLOSS_LIMIT','STOPLOSS_MARKET']
#     producttype=['INTRADAY', 'DELIVERY','CARRYFORWARD','MARGIN','BO' ], exchange=['NSE','BSE','NFO','MCX']

def place_order(symbol, buy_sell, qty, price=None, trigger=None, sl=None, target=None, 
                    variety='NORMAL', ordertype='LIMIT', producttype='INTRADAY', exchange='NSE'):
    buy_sell     =  'BUY' if (buy_sell in ['b','B','buy', 'BUY']) else 'SELL'
    symbol_token =  get_optn_token(symbol, options) if (exchange=='NFO') else get_token(symbol, instrument_list)
    if ordertype == 'SL': variety, ordertype ='STOPLOSS', 'STOPLOSS_LIMIT'
    if (price is None) and (trigger is None): ordertype = 'MARKET'
    orderparams  = {"variety"        : variety,  
                    "tradingsymbol"  : symbol,
                    "symboltoken"    : symbol_token,
                    "transactiontype": buy_sell,
                    "exchange"       : exchange,
                    "ordertype"      : ordertype,
                    "producttype"    : producttype,
                    "duration"       : 'DAY',
                    "price"          : price,
                    "triggerprice"   : trigger,
                    "stoploss"       : sl, #robo order
                    "squareoff"      : target,
                    "quantity"       : qty }   
    return smart.placeOrder(orderparams)

def cancel_order(order_id):
    time.sleep(1)
    order_book = pd.DataFrame(smart.orderBook()['data'])
    variety    = order_book[order_book['orderid']==order_id]['variety'].iloc[0]
    return smart.cancelOrder(order_id=order_id,variety=variety)

def modify_order(order_id, price=None, trigger=None, qty=None):
    time.sleep(1)
    order_book     = pd.DataFrame(smart.orderBook()['data'])
    order_book     = order_book[order_book['orderid']==order_id]
    price          = order_book['price'].iloc[0] if (price==None) else price
    trigger        = order_book['triggerprice'].iloc[0] if (trigger==None) else trigger
    qty            = order_book['quantity'].iloc[0] if (qty==None) else qty
    orderparams    = { "orderid"      : order_id,
                       "duration"     : "DAY",
                       "quantity"     : qty, 
                       "price"        : price,
                       "triggerprice" : trigger,
                       "stoploss"     : order_book['stoploss'     ].iloc[0],
                       "squareoff"    : order_book['squareoff'    ].iloc[0],
                       "variety"      : order_book['variety'      ].iloc[0], 
                       "ordertype"    : order_book['ordertype'    ].iloc[0],
                       "producttype"  : order_book['producttype'  ].iloc[0],
                       "tradingsymbol": order_book['tradingsymbol'].iloc[0],
                       "symboltoken"  : order_book['symboltoken'  ].iloc[0],
                       "exchange"     : order_book['exchange'     ].iloc[0]} 
    return smart.modifyOrder(orderparams)['data']['orderid']

def exit_position(symbol, qty=None):
    Orders = orders()
    if symbol in Orders['tradingsymbol']:
        order_ids = Orders[Orders['tradingsymbol']==symbol]['orderid']
        for order_id in order_ids:
            cancel_order(order_id)     # cancel open orders
    Positions   = positions()
    Positions   = Positions[Positions['netqty']!=0]
    Positions   = Positions[Positions['tradingsymbol'] == symbol]
    producttype = Positions['producttype'].iloc[0]
    exchange    = Positions['exchange'   ].iloc[0]
    qty         = Positions['netqty'     ].iloc[0] if (qty == None) else qty
    buy_sell    = 'BUY' if qty<0 else 'SELL'
    return place_order(symbol, buy_sell, abs(qty), ordertype = 'MARKET', producttype=producttype, exchange=exchange)
  
def orders():
    time.sleep(1)                             # rate limit 1 per second
    Orders=smart.orderBook()['data']
    return pd.DataFrame(Orders)

def trades():
    return pd.DataFrame(smart.tradeBook()['data'])

def order_status(order_id, Orders):           # complete, cancelled, rejected, open, trigger pending
    return Orders[Orders['orderid']==order_id]['orderstatus'].iloc[-1]

def filled_price(order_id, Orders):
    return Orders[Orders['orderid']==order_id]['averageprice'].iloc[-1]

def trigger_price(order_id, Orders):
    return Orders[Orders['orderid']==order_id]['triggerprice'].iloc[-1]

def order_reason(order_id, Orders):
    return Orders[Orders['orderid']==order_id]['text'].iloc[-1]   

def open_orders():
    time.sleep(1)
    Orders=pd.DataFrame(smart.orderBook()['data'])
    return Orders[(Orders['orderstatus']=='open') | (Orders['orderstatus']=='trigger pending')]

def cancel_all_orders():
    all_orders=open_orders()
    all_orders.reset_index(drop=True, inplace=True)
    for i in range(len(all_orders)):
        smart.cancelOrder(order_id=all_orders['orderid'][i], variety=all_orders['variety'][i])
    print(f'Cancelled {len(all_orders)} orders')

# # 3. HISTORICAL DATA
# https://smartapi.angelbroking.com/docs/Historical

# ## 3.1 HTTP CONNECTION

def historical_data(symbol,instrument_list, day_count=5,interval='FIVE_MINUTE',exchange="NSE"):
    if symbol[-3:] in ['0CE', '0PE']: symbol_token, exchange =get_optn_token(symbol,options), 'NFO'   
    else:  
        symbol_token, exchange = get_token(symbol,instrument_list, exchange=exchange), exchange                               
    params = {"exchange": exchange, "symboltoken": symbol_token, "interval": interval,
              "fromdate": (dt.datetime.now()-dt.timedelta(day_count)).strftime('%Y-%m-%d %H:%M'), 
              "todate"  : dt.datetime.now().strftime('%Y-%m-%d %H:%M')}
    historical_data = smart.getCandleData(params)
    df_data = pd.DataFrame(historical_data["data"], columns = ["date","open","high","low","close","volume"])
    df_data.set_index("date",inplace=True)
    df_data.index=pd.to_datetime(df_data.index)
    df_data.index=df_data.index.tz_localize(None)
    return df_data

def historical_data_indicators(stock_df, INDICATORS=['EMA20','EMA5','RSI', 'ADX']):
    stock_df = StockDataFrame.retype(stock_df)
    indicator_codes={'EMA20': 'close_20_ema',
                     'EMA9' : 'close_9_ema' ,
                     'EMA5' : 'close_5_ema' ,
                     'RSI'  : 'rsi_14'      ,
                     'ADX'  : 'adx'         }
    for indicator in INDICATORS:
        if indicator[:3]=='EMA':
            indicator_codes[indicator] = f'close_{indicator[3:]}_ema'
        if indicator[:3] =='SMA':
            indicator_codes[indicator]= f'close_{indicator[3:]}_sma'
    
    indicators = [indicator_codes[i] for i in INDICATORS]
    stock_df[indicators]
    columns  = ['open','high', 'low' ,'close', 'volume'] + indicators
    stock_df = stock_df[columns]
    renamed_columns = dict(zip(indicators, INDICATORS)) #swap key:value pair in indicator_codes dict
    stock_df.rename(columns= renamed_columns, inplace=True)
    stock_df = stock_df.round(1)
    return stock_df



# # 4. STRATEGY

class EMACrossoverStrategy:
    
    def __init__(self, index='BANKNIFTY', interval='FIVE_MIINUTE', lots=1, sl_pts =30, target_pts =120, indicator1='EMA3', indicator2='EMA30', RR=5, expiry=None):  
        self.index             = index          
        self.lots              = lots
        self.expiry            = expiry           # expiry= dt.datetime(2023,10,15)   
        self.sl_pts            = sl_pts
        self.target_pts        = target_pts
        self.RR                = RR
        self.interval          = interval
        self.days              = 3
        self.count             = 1                 # No. of positions allowed at any time
        self.exchange          = 'NFO' 
        self.indicator1        = indicator1
        self.indicator2        = indicator2
        self.open_long         = False
        self.open_short        = False
        self.open_positions    = []
        self.exited_positions  = []
        self.open_positions_df = pd.DataFrame(self.open_positions)
        
        if self.index in ['bnf','BNF','banknifty','BANKNIFTY']: [self.index, self.exchange, self.lot_size, self.index_code, self.strike_interval]=['BANKNIFTY','NFO',15, 'Nifty Bank',100]
        elif self.index in ['fin','FIN','finnifty','FINNIFTY']: [self.index, self.exchange, self.lot_size, self.index_code, self.strike_interval]=['FINNIFTY', 'NFO',40, 'Nifty Fin Service',50]
        elif self.index in ['nif','NIF','nifty','NIFTY'      ]: [self.index, self.exchange, self.lot_size, self.index_code, self.strike_interval]=['NIFTY',    'NFO',50, 'Nifty 50',50]
        elif self.index in ['sen','SEN','sensex','SENSEX'    ]: [self.index, self.exchange, self.lot_size, self.index_code, self.strike_interval]=['SENSEX',   'BFO',10, 'SENSEX',100]
        elif self.index in ['BANKEX', 'bankex'               ]: [self.index, self.exchange, self.lot_size, self.index_code, self.strike_interval]=['BANKEX',   'BFO',15, 'BANKEX',100] 
        self.qty = self.lots*self.lot_size

    def scanner(self):
        
        self.long_signal  = False
        self.short_signal = False
        try:
            self.spot = self.index_code
            a = historical_data(self.spot, instrument_list, day_count=5, interval=self.interval, exchange='NSE')
            a = historical_data_indicators(a, INDICATORS=[self.indicator1, self.indicator2]) 
            a  = a.drop(columns = ['volume'])
            print(a.iloc[-3:])
            self.long_condition1     = (a[self.indicator1].iloc[-2] >= a[self.indicator2].iloc[-2]) & (a[self.indicator1].iloc[-3] < a[self.indicator2].iloc[-3])        # EMA crossover
            self.long_crossover_high = a['high'].iloc[-2]

            self.short_condition1    = (a[self.indicator1].iloc[-2] <= a[self.indicator2].iloc[-2]) & (a[self.indicator1].iloc[-3] > a[self.indicator2].iloc[-3])        # EMA crossover
            self.short_crossover_low = (a['low'].iloc[-2])                                                # price crosses crossover candle low


            # LONG SIGNAL
            if self.long_condition1:
                while self.long_signal==False:
                    ltp = get_ltp(self.spot)
                    self.long_condition2 = (ltp > self.long_crossover_high)
                    if self.long_condition2:
                        print(inst_time(), f'LONG SIGNAL on {self.index}')
                        self.long_signal = True
                        #alert()
                    else: time.sleep(30)

            elif self.short_condition1:
                while self.short_signal==False:
                    ltp = get_ltp(self.spot)
                    self.short_condition2 = (ltp > self.long_crossover_high)
                    if self.short_condition2:
                        print(inst_time(), f'SHORT SIGNAL on {self.index}')
                        self.short_signal = True
                        #alert()
                    else: time.sleep(30)
                    
        except Exception as e: print(str(e))
                                     
    def fresh_execution(self):
        #STRIKE SELECTION
        self.index_spot = get_ltp(self.spot)
        self.ATM_strike = round(self.index_spot/100)*100 if self.strike_interval==100 else int(max(self.index_spot//50*50, (self.index_fut+25)//50*50))
        
        if (self.long_signal == True) and (self.open_long ==False) :
            
            self.call_symbol  = get_optn_symbol(options, index=self.index, strike_price=self.ATM_strike, call_put='c', expiry=self.expiry) 
            self.call_premium = get_ltp(self.call_symbol)

            self.long_call    = place_order(self.call_symbol,'b',self.qty, producttype='CARRYFORWARD', exchange=self.exchange)
            Orders = orders()
            if order_status(self.long_call, Orders) == 'complete':
                entry_price       = filled_price(self.long_call, Orders)
                sl_price          = round(entry_price - self.sl_pts,1)
                target            = round(entry_price + self.target_pts,1)
                self.call_slorder = place_order(self.call_symbol, 's', self.qty,trigger=sl_price, price=sl_price-5, ordertype='SL',producttype='CARRYFORWARD', exchange=self.exchange)

                open_position = {'position'    : 'long',
                                 'symbol'      : self.call_symbol,
                                 'qty'         : self.qty,
                                 'entry_price' : entry_price,
                                 'entry_time'  : inst_time(),
                                 'sl_price'    : sl_price,
                                 'target'      : target,
                                 'order_id'    : self.long_call,
                                 'sl_id'       : self.call_slorder}
                print(open_position)
                self.open_positions.append(open_position)
                self.open_long = True
            else: print(self.call_symbol, order_status(self.long_call, Orders))
            
        elif (self.short_signal == True) and (self.open_short==False):
            
            self.put_symbol   = get_optn_symbol(options, index=self.index, strike_price=self.ATM_strike, call_put='p', expiry=self.expiry) 
            self.put_premium  = get_ltp(self.put_symbol) 

            self.long_put     = place_order(self.put_symbol,'b',self.qty, producttype='CARRYFORWARD',exchange=self.exchange)
            Orders            = orders()
            if order_status(self.long_put, Orders) == 'complete':
                entry_price      = filled_price(self.long_put, Orders)
                sl_price         = round(entry_price - self.sl_pts,1)
                target           = round(entry_price + self.target_pts,1)
                self.put_slorder = place_order(self.put_symbol, 's', self.qty,trigger=sl_price, price=sl_price-5, ordertype='SL', producttype='CARRYFORWARD', exchange=self.exchange)

                open_position = {'position'    : 'short',
                                 'symbol'      : self.put_symbol,
                                 'qty'         : self.qty,
                                 'entry_price' : entry_price,
                                 'entry_time'  : inst_time(),
                                 'sl_price'    : sl_price,
                                 'target'      : target,
                                 'order_id'    : self.long_put,
                                 'sl_id'       : self.put_slorder}
                print(open_position)
                self.open_positions.append(open_position)
                self.open_short = True
            else: print(self.put_symbol, order_status(self.long_put, Orders))
        self.open_positions_df = pd.DataFrame(self.open_positions)
                        
    def exit_conditions(self):
        n=0
        self.exit_condition = False
        try:
            while((self.exit_condition!= True) and (not self.open_positions_df.empty) and (dt.datetime.now().time() < dt.time(15,35))):

                self.symbols      = self.open_positions_df['symbol']
                self.positions    = self.open_positions_df['position']
                self.qtys         = self.open_positions_df['qty']
                self.entry_prices = self.open_positions_df['entry_price']
                self.entry_times  = self.open_positions_df['entry_time']
                self.sl_prices    = self.open_positions_df['sl_price']
                self.targets      = self.open_positions_df['target']
                self.order_ids    = self.open_positions_df['order_id']
                self.sl_ids       = self.open_positions_df['sl_id']

                i = 0
                Orders = orders()
                a = historical_data(self.spot, instrument_list, day_count=3, interval=self.interval, exchange='NSE')
                a = historical_data_indicators(a, INDICATORS=[self.indicator1, self.indicator2])
                ltp = get_ltp(self.symbols[i])
                self.exit_condition1 = order_status(self.sl_ids[i], Orders)=='complete'                     # SL Hit
                self.exit_condition2 = (ltp - self.targets[i] >= 0)                                         # Target reached                           
                self.exit_condition3 = True #(dt.datetime.now().time()>dt.time(15,30))                      # Carry Forward
                self.exit_condition4 = (self.positions[i]=='long' ) and (a[self.indicator1].iloc[-1] <= a[self.indicator2].iloc[-1]) and (a[self.indicator1].iloc[-2] > a[self.indicator2].iloc[-2])  # Reverse crossover
                self.exit_condition5 = (self.positions[i]=='short') and (a[self.indicator1].iloc[-1] >= a[self.indicator2].iloc[-1]) and (a[self.indicator1].iloc[-2] < a[self.indicator2].iloc[-2])  # Reverse crossover

                if any([self.exit_condition1, self.exit_condition2, self.exit_condition4, self.exit_condition5]):
                    if self.exit_condition1:
                        exit_price = filled_price(self.sl_ids[i], Orders)
                        pnl        = (exit_price - self.entry_prices[i])*self.qty
                    else :
                        Cancel_order = cancel_order(self.sl_ids[i])
                        exit_order   = place_order(self.symbols[i],'s',self.qtys[i], producttype='CARRYFORWARD',exchange=self.exchange)
                        Orders       = orders()
                        if order_status(exit_order, Orders) == 'complete':
                            exit_price = filled_price(exit_order, Orders)
                            pnl        = (exit_price - self.entry_prices[i])*self.qtys[i]
                        else:
                            print(f'Unable to exit {self.symbols[i]}')
                            #alert(2)

                    exited_position =  { 'position'    : self.positions[i],
                                         'symbol'      : self.symbols[i],
                                         'qty'         : self.qtys[i],
                                         'entry_time'  : self.entry_times[i],
                                         'entry_price' : self.entry_prices[i],
                                         'exit_price'  : exit_price,
                                         'exit_time'   : inst_time(),
                                         'pnl'         : round(pnl,1)}
                    print(exited_position)
                    if (self.positions[i]=='long'): self.open_long = False 
                    else :   self.open_short = False
                    self.exited_positions.append(exited_position)
                    self.open_positions.remove(self.open_positions[i])
                    self.open_positions_df   = pd.DataFrame(self.open_positions)
                    self.exited_positions_df = pd.DataFrame(self.exited_positions)
                    self.exit_condition      = True

                self.open_positions_df = pd.DataFrame(self.open_positions)
                time.sleep(15)
                print('.', end='')
                
        except Exception as e: print(str(e))
        
    def renew_connection(self):
        print(self.open_positions_df)
        self.exit_conditions()
    
    def main_execution(self):
        if self.open_positions:
            self.renew_connection()
        else:
            while(dt.time(9,20) < dt.datetime.now().time() < dt.time(15,30)):
                #if (dt.datetime.now().time().minute % 5 ==0):
                self.scanner()
                if any([self.long_signal, self.short_signal]):
                    self.fresh_execution()
                    if self.open_positions: self.exit_conditions()    
                    else : self.main_execution()

                time.sleep(30)
                print('.', end='')
                
# ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# # 5. LIVE EXECUTION
# ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

strategy = EMACrossoverStrategy(index='BANKNIFTY', interval='FIVE_MINUTE', lots=1, sl_pts =30, target_pts =120, indicator1='EMA3', indicator2='EMA30', RR=5, expiry=None)
print('EMA Crossover Strategy')
strategy.main_execution()

