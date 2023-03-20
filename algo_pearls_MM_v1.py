"""
The python module to be uploaded to the website, with the algorithmic trading logic
The log tracks all print commands
"""
from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import numpy as np

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

assets = {
    "PEARLS":Asset(20, 10, 10),
    "BANANAS":Asset(20, 100, 50),
}
class Trader:
    """
    The trader class, containing a run method which runs the trading algo
    """
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        result = {}
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
                    print('sell if')
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
                                print('MISSED buy of ',product, str(order_size) + "x", ask, 'position:', position)
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
                    order_size = np.floor(5*(1-position/20))
                    bid = max(order_depth.buy_orders.keys())+spread-5
                    orders.append(Order(product, bid, order_size))
                    print("MM BUY", product, str(order_size) + "x", bid, 'position:', position)
                    #ask
                    order_size = -np.floor(5*(1+position/20))
                    ask = min(order_depth.sell_orders.keys())-spread+5
                    orders.append(Order(product, ask, order_size))
                    print("MM SELL", product, str(-order_size) + "x", ask,  'position:', position)

                # Add all the above orders to the result dict
                result[product] = orders
            if product == 'BANANAS':
                None
        # Return the dict of orders
        return result
