"""
The python module to be uploaded to the website, with the algorithmic trading logic
The log tracks all print commands
"""

import numpy as np
from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order

# import numpy
# import math
# import statistics
def limtransform(pos, max_limit, buyers, sellers):
    if abs(np.floor(5*(1-(sellers*pos/max_limit*buyers)))) > abs(0.75*max_limit - pos):
        return abs(0.75*max_limit - pos)
    else:
        return abs(np.floor(5*(1-(sellers*pos/max_limit*buyers))))
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


class Trader:
    """
    The trader class, containing a run method which runs the trading algo
    """
    def __init__(self, assets = None, printing = True):
        if assets is None:
            assets = {
                "PEARLS":Asset(20, 10, 10),
                "BANANAS":Asset(20, 10, 10),
            }
        self.asset_dicts = assets
        self.printing = printing
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        assets = self.asset_dicts
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
                    min_profit = 0
                    for ask in asks:
                        if ask < acceptable_price-min_profit:
                            vol = order_depth.sell_orders[ask]
                            order_size = min(-vol, assets[product].limit-position)
                            if order_size > 0:
                                position = position + order_size
                                print("BUY", product, str(order_size) + "x", ask, 'position:', position)
                                orders.append(Order(product, ask, order_size))
                            else:
                                print('MISSED buy of ',product, str(vol) + "x", ask, 'position:', position)
                    assets[product].update_ask_prices(asks[0])

                if len(order_depth.buy_orders) != 0:
                    available_to_sell = True # other people are buying ergo we can sell
                    # sell everything above our acceptable price
                    bids = list(order_depth.buy_orders.keys())
                    bids = sorted(bids, reverse=True)
                    for bid in bids:
                        if bid > acceptable_price:
                            vol = order_depth.buy_orders[bid]
                            order_size = min(vol, assets[product].limit+position)
                            if order_size > 0:
                                position = position - order_size
                                print("SELL", product, str(order_size) + "x", bid,  'position:', position)
                                orders.append(Order(product, bid, -order_size))
                            else:
                                print('MISSED sell of ',product, str(vol) + "x", bid, 'position:', position)
                    assets[product].update_bid_prices(bids[0])

                #MarketMaking
                # Retrieve the Order Depth containing all the market BUY and SELL orders for PEARLS
                order_depth: OrderDepth = state.order_depths[product]
                threshold = 6
                spread = min(list(order_depth.sell_orders.keys()))-max(list(order_depth.buy_orders.keys()))
                if spread >= threshold:
                    #adjust volumes later
                    #bid
                    bid_size = np.floor(10*(1-position/20))
                    bid = max(order_depth.buy_orders.keys())+1
                    orders.append(Order(product, bid, bid_size))
                    #print('Spread: ', spread, "MM BUY", product, str(bid_size) + "x", bid, 'position:', position)
                    #ask
                    ask_size = -np.floor(10*(1+position/20))
                    ask = min(order_depth.sell_orders.keys())-1
                    orders.append(Order(product, ask, ask_size))
                    print('Spread:', spread, "MM BUY", product, str(bid_size) + "x", bid, 'position:', position, "MM SELL", product, str(-ask_size) + "x", ask,  'position:', position)

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

                # If statement checks if there are any SELL orders in the BANANAS market
                if len(order_depth.sell_orders) > 0:
                    best_ask = min(order_depth.sell_orders.keys())
                    best_ask_volume = order_depth.sell_orders[best_ask]
                    assets[product].update_ask_prices(best_ask)

                if len(order_depth.buy_orders) != 0:
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    assets[product].update_bid_prices(best_bid)

                spread = best_ask-best_bid
                threshold = 5
                if spread < threshold:
                    if len(assets[product].ask_prices)>=assets[product].period:
                        fast_avg = (sum(assets[product].ask_prices[-assets[product].fast_period:])+sum(assets[product].bid_prices[-assets[product].fast_period:]))/(2*assets[product].fast_period)
                        #check for buy signal
                        if fast_avg > best_ask:
                            #available_to_buy = True
                            order_size = min(-best_ask_volume, assets[product].limit-position)
                            if order_size > 0:
                                print("BUY", product, str(order_size) + "x", best_ask)
                                orders.append(Order(product, best_ask, order_size))
                        #check for sell signal
                        elif fast_avg < best_bid:
                            #available_to_sell = True
                            order_size = min(best_bid_volume, assets[product].limit+position)
                            if order_size > 0:
                                print("SELL", product, str(order_size) + "x", best_bid)
                                orders.append(Order(product, best_bid, -order_size))

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
