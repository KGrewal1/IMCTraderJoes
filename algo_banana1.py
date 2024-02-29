"""
The python module to be uploaded to the website, with the algorithmic trading logic
The log tracks all print commands
"""
from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order

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

assets = {
    "PEARLS":Asset(20, 10, 10),
    "BANANAS":Asset(20, 30, 25),
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
                None
                #add later
                
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

                # If statement checks if there are any SELL orders in the BANANAS market
                if len(order_depth.sell_orders) > 0:

                    # Sort all the available sell orders by their price,
                    # and select only the sell order with the lowest price
                    available_to_buy = True # other people are selling ergo we can buy
                    best_ask = min(order_depth.sell_orders.keys())
                    best_ask_volume = order_depth.sell_orders[best_ask]
                    assets[product].update_ask_prices(best_ask)

                if len(order_depth.buy_orders) != 0:
                    available_to_sell = True # other people are buying ergo we can sell
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    assets[product].update_bid_prices(best_bid)

                if (len(assets[product].ask_prices)<assets[product].period) and (len(assets[product].bid_prices)<assets[product].period):
                    available_to_buy = False
                else:
                    fast_avg = (sum(assets[product].ask_prices[-assets[product].fast_period:])+sum(assets[product].bid_prices[-assets[product].fast_period:]))/(2*assets[product].fast_period)
                    #print("delta", slow_avg, fast_avg)
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
             
                # Add all the above orders to the result dict
                result[product] = orders

        # Return the dict of orders
        return result