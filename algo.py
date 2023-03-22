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

                # Retrieve the Order Depth containing all the market BUY and SELL orders for PEARLS
                order_depth: OrderDepth = state.order_depths[product]
                timestamp = state.timestamp
                new_row = {'timestamp':timestamp}
                try:
                    position = state.position[product]
                except KeyError:
                    position = 0
                new_row['position'] = position
                # Initialize the list of Orders to be sent as an empty list
                orders: list[Order] = []

                # to see if there are available trades in the market
                available_to_buy = False
                available_to_sell = False

                # If statement checks if there are any SELL orders in the PEARLS market
                if len(order_depth.sell_orders) > 0:

                    # Sort all the available sell orders by their price,
                    # and select only the sell order with the lowest price
                    available_to_buy = True # other people are selling ergo we can buy
                    best_ask = min(order_depth.sell_orders.keys())
                    best_ask_volume = order_depth.sell_orders[best_ask]
                    new_row['best_ask'], new_row['best_ask_volume'] = best_ask, best_ask_volume

                if len(order_depth.buy_orders) > 0:
                    available_to_sell = True # other people are buying ergo we can sell
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    new_row['best_bid'], new_row['best_bid_volume'] = best_bid, best_bid_volume

                mid_price = (best_bid+best_ask)/2
                weighted_mid_price = (best_bid*best_bid_volume-best_ask*best_ask_volume)/(best_bid_volume-best_ask_volume)
                new_row['mid_price'], new_row['weighted_mid_price'] = mid_price, weighted_mid_price
                self.asset_dicts[product].historic_data = pd.concat([self.asset_dicts[product].historic_data , pd.DataFrame([new_row])], ignore_index=True)

                if len(self.asset_dicts[product].historic_data.index)<self.asset_dicts[product].period+1:
                    available_to_sell = False
                    available_to_buy = False
                else:
                    # slow_avg = self.asset_dicts[product].historic_data['mid_price'].ewm(halflife = self.asset_dicts[product].period).mean().iloc[-1]
                    # fast_ask_avg = self.asset_dicts[product].historic_data['best_ask'].ewm(halflife = self.asset_dicts[product].fast_period).mean().iloc[-1]
                    # # fast_bid_avg = self.asset_dicts[product].historic_data['best_bid'].ewm(halflife = self.asset_dicts[product].fast_period).mean().iloc[-1] #.pct_change()
                    # pct_change = self.asset_dicts[product].historic_data['mid_price'].pct_change().iloc[-1]
                    # rsi_sma = calc_rsi(self.asset_dicts[product].historic_data['mid_price'], lambda s: s.rolling(self.asset_dicts[product].period).mean(), self.asset_dicts[product].period).iloc[-1]
                    mid_short_average = self.asset_dicts[product].historic_data['mid_price'].rolling(window = self.asset_dicts[product].fast_period).mean()
                    if mid_short_average.iloc[-1] > best_ask:
                        available_to_buy = True
                    if mid_short_average.iloc[-1] < best_bid:
                        available_to_sell = True
                    # velocity = pd.Series(mid_short_average.diff(1)).rolling(window = 150).mean()
                    # last_velocity = velocity.iloc[-2]
                    # current_velocity = velocity.iloc[-1]
                    # sign_change = np.sign(current_velocity)*np.sign(last_velocity)
                    # # print(np.sign(last_velocity), np.sign(current_velocity), np.sign(current_velocity)*np.sign(last_velocity))
                    # if sign_change == -1:
                    #     print(state.timestamp)
                    #     # going negative to positive
                    #     if np.sign(last_velocity) ==1:
                    #         available_to_sell = True
                    #         available_to_buy = False
                    #         self.asset_dicts[product].last_signal = -1
                    #     # going positive to negative
                    #     elif np.sign(last_velocity) ==-1:
                    #         available_to_buy = True
                    #         available_to_sell = False
                    #         self.asset_dicts[product].last_signal = 1
                    # else:
                    #     available_to_buy = False
                    #     available_to_sell = False

                    # new_zeros = np.where(np.diff(np.signbit(velocity)))[0]
                    #print(rsi_sma)
                    # # if self.printing: print("delta", slow_avg, fast_avg)
                    # if rsi_sma > 53:#slow_avg+0.2 > fast_bid_avg and self.asset_dicts[product].last_buy>-1:
                    #     available_to_sell = True
                    #     if self.printing:
                    #         print('try to sell')
                    #     self.asset_dicts[product].last_signal = -1
                    # else:
                    #     available_to_sell = False


                    # if rsi_sma < 47:#slow_avg < fast_ask_avg and self.asset_dicts[product].last_buy>-1:
                    #     available_to_buy = True
                    #     if self.printing:
                    #         print('try to buy')
                    #     self.asset_dicts[product].last_signal = 1
                    # else:
                    #     available_to_buy = False

                if available_to_buy or self.asset_dicts[product].last_signal == 1: # best_ask < bid_pred and

                    order_size = min(-best_ask_volume, self.asset_dicts[product].limit-position)
                    if order_size > 0:
                        if self.printing:
                            print("BUY", product, str(order_size) + "x", best_ask)
                        orders.append(Order(product, best_ask, order_size))
                        self.asset_dicts[product].last_buy = 0
                    else:
                        self.asset_dicts[product].last_buy += 1
                else:
                    self.asset_dicts[product].last_buy += 1


                # Check if the highest bid is higher than the above defined fair value
                if available_to_sell or self.asset_dicts[product].last_signal == -1: # best_bid > ask_pred and
                    order_size = min(best_bid_volume, self.asset_dicts[product].limit+position)
                    if order_size > 0:
                        if self.printing:
                            print("SELL", product, str(order_size) + "x", best_bid)
                        orders.append(Order(product, best_bid, -order_size))
                        self.asset_dicts[product].last_sell = 0
                    else:
                        self.asset_dicts[product].last_sell += 1
                else:
                    self.asset_dicts[product].last_sell += 1

                # Add all the above orders to the result dict
                if self.printing:
                    print("last sell", self.asset_dicts[product].last_sell, 'last buy', self.asset_dicts[product].last_buy)
                # print(self.asset_dicts[product].historic_data.tail(2))
                result[product] = orders

        # Return the dict of orders
        return result
