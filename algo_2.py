"""
The python module to be uploaded to the website, with the algorithmic trading logic
The log tracks all print commands
"""
from typing import Dict, List, Callable
from datamodel import OrderDepth, TradingState, Order
import pandas as pd
import numpy as np
# import numpy
# import math
# import statistics
def linreg(X, Y):
    """
    linear regression: not entirely convinvced numpy works properly in Prosperity
    """
    N = len(X)
    Sx = Sy = Sxx = Syy = Sxy = 0.0
    for x, y in zip(X, Y):
        Sx = Sx + x
        Sy = Sy + y
        Sxx = Sxx + x*x
        Syy = Syy + y*y
        Sxy = Sxy + x*y
    det = Sxx * N - Sx * Sx
    return (Sxy * N - Sy * Sx)/det, (Sxx * Sy - Sx * Sxy)/det

def calc_rsi(over: pd.Series, fn_roll: Callable, window) -> pd.Series:
    """Function to calculate RSI"""
    # Get the difference in price from previous step
    delta = over.diff()
    # Get rid of the first row, which is NaN since it did not have a previous row to calculate the differences
    delta = delta[1:]

    # Make the positive gains (up) and negative gains (down) Series
    up, down = delta.clip(lower=0), delta.clip(upper=0).abs()

    roll_up, roll_down = fn_roll(up), fn_roll(down)
    rs = roll_up / roll_down
    rsi = 100.0 - (100.0 / (1.0 + rs))

    # Avoid division-by-zero if `roll_down` is zero
    # This prevents inf and/or nan values.
    rsi[:] = np.select([roll_down == 0, roll_up == 0, True], [100, 0, rsi])
    rsi.name = 'rsi'

    # Assert range
    valid_rsi = rsi[window - 1:]
    assert ((0 <= valid_rsi) & (valid_rsi <= 100)).all()
    # Note: rsi[:length - 1] is excluded from above assertion because it is NaN for SMA.

    return rsi
# asset class: stores info about an asset not in the datamodel
class Asset:
    """asset class to contain previous prices, and the limits for an asset"""
    def __init__(self, limit, period, fast_period):
        self.limit = limit
        self.period = period
        self.fast_period = fast_period
        self.last_buy = 0
        self.last_sell = 0
        self.last_buy_price = 0
        self.last_sell_price = 1000000
        self.last_signal = 0
        self.historic_data = pd.DataFrame(columns=['timestamp', 'position', 'best_ask', 'best_ask_volume', 'best_bid', 'best_bid_volume', 'mid_price', 'weighted_mid_price'])
    def add_row(self, dic):
        self.historic_data = self.historic_data.iloc[-self.period:]
        self.historic_data = pd.concat([self.historic_data , pd.DataFrame([dic])], ignore_index=True)

    # def update_ask_prices(self, ask_price):
    #     """update the period most recent ask prices"""
    #     if len(self.ask_prices)<self.period:
    #         self.ask_prices.append(ask_price)
    #     else:
    #         self.ask_prices.pop(0)
    #         self.ask_prices.append(ask_price)
    # def update_bid_prices(self, bid_price):
    #     """update the period most recent ask prices"""
    #     if len(self.bid_prices)<self.period:
    #         self.bid_prices.append(bid_price)
    #     else:
    #         self.bid_prices.pop(0)
    #         self.bid_prices.append(bid_price)
    # def __str__(self) -> str:
    #     return ('Limit '+str(self.limit)+' long average '+str(self.period)+' short average '
    #             +str(self.fast_period)
    #             + '\n' + str(self.bid_prices) + "\n"+ str(self.ask_prices))

def sigmoid(L):
    return(3*(1-abs(L)/4)*L/(1+abs(2*L)))
def limtransform(pos, max_limit, buyers, sellers):
    if abs(np.floor(5*(1-(sellers*pos/max_limit*buyers)))) > abs(0.75*max_limit - pos):
        print(abs(0.75*max_limit - pos))
        return abs(0.75*max_limit - pos)
    else:
        print(abs(0.75*max_limit - pos), np.floor(5*(1-(sellers*pos/max_limit*buyers))))
        return abs(np.floor(5*(1-(sellers*pos/max_limit*buyers))))

class Trader:
    """
    The trader class, containing a run method which runs the trading algo
    """
    def __init__(self, asset_dicts = None, printing = True):
        if asset_dicts is None:
            asset_dicts = {
                "PEARLS":Asset(20, 10, 10),
                "BANANAS":Asset(20, 90, 15),
            }
        self.asset_dicts = asset_dicts
        self.printing = printing
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        result = {}
        # print(state.market_trades)
        # Iterate over all the keys (the available products) contained in the order depths
        for product in state.order_depths.keys():
            if product == 'BANANAS':

                order_depth: OrderDepth = state.order_depths[product]
                try:
                    position = state.position[product]
                except KeyError:
                    position = 0
                # Initialize the list of Orders to be sent as an empty list
                orders: list[Order] = []
                threshold = 5
                best_ask = min(order_depth.sell_orders.keys())
                best_ask_volume = order_depth.sell_orders[best_ask]
                best_bid = max(order_depth.buy_orders.keys())
                best_bid_volume = order_depth.buy_orders[best_bid]
                spread = best_ask-best_bid
                if spread >= threshold:
                    #adjust volumes later
                    #bid
                    order_size = limtransform(position, 20, abs(best_bid_volume), abs(best_ask_volume)) # np.floor(5*(1-position/20))
                    bid = max(order_depth.buy_orders.keys())+1
                    orders.append(Order(product, bid, order_size))
                    print(spread)
                    print("MM BUY", product, str(order_size) + "x", bid, 'position:', position)
                    #ask
                    order_size = -limtransform(-position, 20, abs(best_ask_volume), abs(best_bid_volume))  # -np.floor(5*(1+position/20))
                    ask = min(order_depth.sell_orders.keys())-1
                    orders.append(Order(product, ask, order_size))
                    print("MM SELL", product, str(-order_size) + "x", ask,  'position:', position)

                # Add all the above orders to the result dict
                result[product] = orders

        # Return the dict of orders
        return result
