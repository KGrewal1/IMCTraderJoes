"""
The python module to be uploaded to the website, with the algorithmic trading logic
The log tracks all print commands
"""
from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
# import pandas
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

# asset class: stores info about an asset not in the datamodel
class Asset:
    """asset class to contain previous prices, and the limits for an asset"""
    def __init__(self, limit, period, fast_period):
        self.limit = limit
        self.ask_prices = []
        self.bid_prices = []
        self.period = period
        self.fast_period = fast_period
    def update_ask_prices(self, ask_price):
        """update the period most recent ask prices"""
        if len(self.ask_prices)<self.period:
            self.ask_prices.append(ask_price)
        else:
            self.ask_prices.pop(0)
            self.ask_prices.append(ask_price)
    def update_bid_prices(self, bid_price):
        """update the period most recent ask prices"""
        if len(self.bid_prices)<self.period:
            self.bid_prices.append(bid_price)
        else:
            self.bid_prices.pop(0)
            self.bid_prices.append(bid_price)
    def __str__(self) -> str:
        return ('Limit '+str(self.limit)+' long average '+str(self.period)+' short average '
                +str(self.fast_period)
                + '\n' + str(self.bid_prices) + "\n"+ str(self.ask_prices))

assets = {
    "PEARLS":Asset(20, 10, 10),
    "BANANAS":Asset(20, 90, 15),
}
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

            if product == 'PEARLS':

                # Retrieve the Order Depth containing all the market BUY and SELL orders for PEARLS
                order_depth: OrderDepth = state.order_depths[product]
                try:
                    position = state.position[product]
                except KeyError:
                    position = 0
                # Initialize the list of Orders to be sent as an empty list
                orders: list[Order] = []

                # Define a fair value for the PEARLS.
                acceptable_price = 10000

                # to see if there are available trades in the market
                available_to_buy = False
                available_to_sell = False

                # If statement checks if there are any SELL orders in the PEARLS market
                if len(order_depth.sell_orders) > 0:

                    available_to_buy = True # other people are selling ergo we can buy
                    # buy everything below our acceptable price
                    asks = list(order_depth.sell_orders.keys())
                    asks = sorted(asks)
                    for ask in asks:
                        if ask < acceptable_price:
                            vol = order_depth.sell_orders[ask]
                            order_size = min(-vol, self.asset_dicts[product].limit-position)
                            if order_size > 0:
                                position = position + order_size
                                if self.printing: print("BUY", product, str(order_size) + "x", ask)
                                orders.append(Order(product, ask, order_size))
                    self.asset_dicts[product].update_ask_prices(asks[0])

                if len(order_depth.buy_orders) != 0:
                    available_to_sell = True # other people are buying ergo we can sell
                    # sell everything above our acceptable price
                    bids = list(order_depth.buy_orders.keys())
                    bids = sorted(bids, reverse=True)
                    for bid in bids:
                        if bid > acceptable_price:
                            vol = order_depth.buy_orders[bid]
                            order_size = min(vol, self.asset_dicts[product].limit+position)
                            if order_size > 0:
                                position = position - order_size
                                if self.printing: print("SELL", product, str(order_size) + "x", bid)
                                orders.append(Order(product, bid, -order_size))
                    self.asset_dicts[product].update_bid_prices(bids[0])



                # Add all the above orders to the result dict
                result[product] = orders
            if product == 'BANANAS':

                # Retrieve the Order Depth containing all the market BUY and SELL orders for PEARLS
                order_depth: OrderDepth = state.order_depths[product]

                try:
                    position = state.position[product]
                except KeyError:
                    position = 0
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
                    self.asset_dicts[product].update_ask_prices(best_ask)

                if len(order_depth.buy_orders) != 0:
                    available_to_sell = True # other people are buying ergo we can sell
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    self.asset_dicts[product].update_bid_prices(best_ask)

                if len(self.asset_dicts[product].ask_prices)<self.asset_dicts[product].period:
                    available_to_buy = False
                    ask_pred = 0
                else:
                    slow_avg = sum(self.asset_dicts[product].ask_prices)/self.asset_dicts[product].period
                    fast_avg = sum(self.asset_dicts[product].ask_prices[-self.asset_dicts[product].fast_period:])/self.asset_dicts[product].fast_period
                    a,b = linreg(range(self.asset_dicts[product].period),self.asset_dicts[product].ask_prices)
                    ask_pred = a*self.asset_dicts[product].period + b
                    if self.printing: print("delta", slow_avg, fast_avg)
                    if slow_avg > fast_avg:
                        available_to_buy = True
                    else:
                        available_to_buy = False


                if len(self.asset_dicts[product].bid_prices)<self.asset_dicts[product].period:
                    available_to_sell = False
                    bid_pred = 100000
                else:
                    slow_avg = sum(self.asset_dicts[product].bid_prices)/self.asset_dicts[product].period
                    fast_avg = sum(self.asset_dicts[product].bid_prices[-self.asset_dicts[product].fast_period:])/self.asset_dicts[product].fast_period
                    a,b = linreg(range(self.asset_dicts[product].period),self.asset_dicts[product].bid_prices)
                    bid_pred = a*self.asset_dicts[product].period + b
                    if self.printing: print("delta", slow_avg, fast_avg)
                    if slow_avg < fast_avg:
                        available_to_sell = True
                    else:
                        available_to_sell = False

                # Check if the lowest ask (sell order) is lower than the above defined fair value
                if available_to_buy and best_ask < 4935: # best_ask < bid_pred and

                    order_size = min(-best_ask_volume, self.asset_dicts[product].limit-position)
                    if order_size > 0:
                        if self.printing: print("BUY", product, str(order_size) + "x", best_ask)
                        orders.append(Order(product, best_ask, order_size))

                # Check if the highest bid is higher than the above defined fair value
                if available_to_sell and best_bid > 4950: # best_bid > ask_pred and
                    order_size = min(best_bid_volume, self.asset_dicts[product].limit+position)
                    if order_size > 0:
                        if self.printing: print("SELL", product, str(order_size) + "x", best_bid)
                        orders.append(Order(product, best_bid, -order_size))

                # Add all the above orders to the result dict
                result[product] = orders

        # Return the dict of orders
        return result
