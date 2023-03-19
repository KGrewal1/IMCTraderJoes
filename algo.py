"""
The python module to be uploaded to the website, with the algorithmic trading logic
The log tracks all print commands
"""
from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order


# dictionary of position limits
limits = {
    "PEARLS":20,
    "BANANAS": 20
}
past_prices = {
    "PEARLS":{},
    "BANANAS": {}
}
# asset class: stores info about an asset not in the datamodel
class asset:
    """asset class to contain previous prices, and the limits for an asset"""
    def __init__(self, limit, period):
        self.limit = limit
        self.ask_prices = []
        self.bid_prices = []
        self.period = period
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
    "PEARLS":asset(20, 10),
    "BANANAS": asset(20, 10),
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

            # Check if the current product is the 'PEARLS' product, only then run the order logic
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
                # Note that this value of 10K is just a dummy value, you should likely change it!
                acceptable_price = 10000

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
                    assets[product].update_ask_prices(best_ask)
                # The below code block is similar to the one above,
                # the difference is that it finds the highest bid (buy order)
                # If the price of the order is higher than the fair value
                # This is an opportunity to sell at a premium
                if len(order_depth.buy_orders) != 0:
                    available_to_sell = True # other people are buying ergo we can sell
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    assets[product].update_bid_prices(best_ask)

                # Check if the lowest ask (sell order) is lower than the above defined fair value
                if best_ask < acceptable_price and available_to_buy:

                    # In case the lowest ask is lower than our fair value,
                    # This presents an opportunity for us to buy cheaply
                    # The code below therefore sends a BUY order at the price level of the ask,
                    # with the same quantity
                    # We expect this order to trade with the sell order
                    order_size = min(-best_ask_volume, assets[product].limit-position)
                    print("BUY", product, str(order_size) + "x", best_ask)
                    orders.append(Order(product, best_ask, order_size))

                # Check if the highest bid is higher than the above defined fair value
                if best_bid > acceptable_price and available_to_sell:
                    order_size = min(best_bid_volume, assets[product].limit+position)
                    print("SELL", product, str(order_size) + "x", best_bid)
                    orders.append(Order(product, best_bid, -order_size))

                # Add all the above orders to the result dict
                result[product] = orders

                # Return the dict of orders
                # These possibly contain buy or sell orders for PEARLS
                # Depending on the logic above
        return result
