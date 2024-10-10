import requests
import talib
import numpy as np
import pandas as pd
from datetime import datetime
from binance.client import Client

# Your Binance API keys
API_KEY = ''
API_SECRET = ''

client = Client(api_key=API_KEY, api_secret=API_SECRET)

def get_historical_data(symbol, interval, start_str, end_str=None):
    klines = client.futures_historical_klines(symbol, interval, start_str, end_str=end_str)
    data = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    data.set_index('timestamp', inplace=True)
    data = data.astype(float)
    return data

def backtest(symbol, short_ema_period, long_ema_period, interval, leverage, percentage, start_date, end_date):
    data = get_historical_data(symbol, interval, start_date, end_date)
    data['short_ema'] = talib.EMA(data['close'], timeperiod=short_ema_period)
    data['long_ema'] = talib.EMA(data['close'], timeperiod=long_ema_period)

    initial_balance = 10000  # Initial balance in USDT
    balance = initial_balance
    position_size = 0
    position_entry_price = 0
    current_position = 'flat'  # 'flat', 'long', 'short'

    # Store trade details
    trades = []

    for index, row in data.iterrows():
        if row['short_ema'] > row['long_ema'] and current_position != 'long':
            if current_position == 'short':
                # Close short position
                pnl = position_size * (position_entry_price - row['close']) * leverage
                balance += pnl
                trades.append({
                    'sell_date': index,
                    'sell_price': row['close'],
                    'position': 'short',
                    'profit': pnl,
                    'balance': balance
                })
                position_size = 0
            # Open long position
            position_size = (balance * percentage / 100) / row['close']
            position_entry_price = row['close']
            current_position = 'long'
            trades.append({
                'buy_date': index,
                'buy_price': row['close'],
                'position': 'long'
            })

        elif row['short_ema'] < row['long_ema'] and current_position != 'short':
            if current_position == 'long':
                # Close long position
                pnl = position_size * (row['close'] - position_entry_price) * leverage
                balance += pnl
                trades.append({
                    'sell_date': index,
                    'sell_price': row['close'],
                    'position': 'long',
                    'profit': pnl,
                    'balance': balance
                })
                position_size = 0
            # Open short position
            position_size = (balance * percentage / 100) / row['close']
            position_entry_price = row['close']
            current_position = 'short'
            trades.append({
                'buy_date': index,
                'buy_price': row['close'],
                'position': 'short'
            })

    # Close any open position at the end
    if current_position == 'long':
        pnl = position_size * (data.iloc[-1]['close'] - position_entry_price) * leverage
        balance += pnl
        trades.append({
            'sell_date': data.index[-1],
            'sell_price': data.iloc[-1]['close'],
            'position': 'long',
            'profit': pnl,
            'balance': balance
        })
    elif current_position == 'short':
        pnl = position_size * (position_entry_price - data.iloc[-1]['close']) * leverage
        balance += pnl
        trades.append({
            'sell_date': data.index[-1],
            'sell_price': data.iloc[-1]['close'],
            'position': 'short',
            'profit': pnl,
            'balance': balance
        })

    return trades



if __name__ == "__main__":
    symbol = "BTCUSDT"
    short_ema_period = 9
    long_ema_period = 30
    interval = "1w"
    leverage = 5
    percentage = 20
    start_date = "2019-01-01"
    end_date = "2024-03-20"

    trades = backtest(symbol, short_ema_period, long_ema_period, interval, leverage, percentage, start_date, end_date)
    total_profit = sum(trade['profit'] for trade in trades if 'profit' in trade)
    final_balance = trades[-1]['balance'] if trades else 0

    print("Trade Details:")
    for trade in trades:
        print(trade)
    print(f"Total Profit: {total_profit} USDT")
    print(f"Final Balance: {final_balance} USDT")
