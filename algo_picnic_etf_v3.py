"""
The python module to be uploaded to the website, with the algorithmic trading logic
The log tracks all print commands
"""

import numpy as np
from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order

def limtransform(pos, max_limit, buyers, sellers):
    if abs(np.floor(5*(1-(sellers*pos/max_limit*buyers)))) > abs(0.75*max_limit - pos):
        return abs(0.75*max_limit - pos)
    else:
        return abs(np.floor(5*(1-(sellers*pos/max_limit*buyers))))

def linear(pos, limit, base):
    return np.floor(base*(1-pos/limit))
# asset class: stores info about an asset not in the datamodel
class Asset:
    """asset class to contain previous prices, and the limits for an asset"""
    def __init__(self, limit, period, fast_period):
        self.limit = limit
        self.ask_prices = []
        self.bid_prices = []
        self.residual = []
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
    def update_residual(self, res):
        """update the period most recent ask prices"""
        if len(self.residual)<self.period:
            self.residual.append(res)
        else:
            self.residual.pop(0)
            self.residual.append(res)


class Trader:
    """
    The trader class, containing a run method which runs the trading algo
    """
    def __init__(self, assets = None, printing = True):
        if assets is None:
            assets = {
                "PEARLS":Asset(20, 10, 10),
                "BANANAS":Asset(20, 10, 10),
                "COCONUTS":Asset(600, 670, 10),
                "PINA_COLADAS":Asset(300, 670, 10),
                "DIP": Asset(300, 10, 10),
                "BAGUETTE": Asset(150, 10, 10),
                "UKULELE": Asset(70, 10, 10),
                "PICNIC_BASKET": Asset(70, 250, 10)
            }
        self.asset_dicts = assets
        self.printing = printing
        self.position = {"PEARLS": 0, "BANANAS": 0,
                        "COCONUTS": 0, "PINA_COLADAS": 0,
                        "DIP": 0, "BAGUETTE": 0, "UKULELE": 0, "PICNIC_BASKET": 0}
        #basket
        self.res_basket = []
        self.zscore_basket = 0
        self.zscore_low = 0.5 #edit
        self.zscore_high = 2.5
        
    def get_data(self, order_depth):
                if len(order_depth.sell_orders) > 0:
                    best_ask = min(order_depth.sell_orders.keys())
                    best_ask_volume = order_depth.sell_orders[best_ask]
                if len(order_depth.buy_orders) != 0:
                    best_bid = max(order_depth.buy_orders.keys())
                    best_bid_volume = order_depth.buy_orders[best_bid]
                    mid = (best_ask+best_bid)/2
                return best_ask, best_ask_volume, best_bid, best_bid_volume, mid
    
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        assets = self.asset_dicts
        # Initialize the method output dict as an empty dict
        result = {}
        # Iterate over all the keys (the available products) contained in the order depths

        # ETF of picnic basket
        orders_dip: list[Order] = []
        orders_baguette: list[Order] = []
        orders_ukulele: list[Order] = []
        orders_basket: list[Order] = []    
        
        #get data
        order_depth_dip = state.order_depths["DIP"]
        best_ask_dip, best_ask_volume_dip, best_bid_dip, best_bid_volume_dip, mid_dip = self.get_data(
            order_depth_dip)
        order_depth_baguette = state.order_depths["BAGUETTE"]
        best_ask_baguette, best_ask_volume_baguette, best_bid_baguette, best_bid_volume_baguette, mid_baguette = self.get_data(
            order_depth_baguette)
        order_depth_ukulele = state.order_depths["UKULELE"]
        best_ask_ukulele, best_ask_volume_ukulele, best_bid_ukulele, best_bid_volume_ukulele, mid_ukulele = self.get_data(
            order_depth_ukulele)
        order_depth_basket = state.order_depths["PICNIC_BASKET"]
        best_ask_basket, best_ask_volume_basket, best_bid_basket, best_bid_volume_basket, mid_basket = self.get_data(
            order_depth_basket)
        
        #positions
        position_baguette = state.position.get('BAGUETTE', 0)
        position_dip = state.position.get('DIP', 0)
        position_ukulele = state.position.get('UKULELE', 0)
        position_basket = state.position.get('PICNIC_BASKET', 0)
        
        # Calculate residuals
        if all([mid_dip, mid_baguette, mid_ukulele, mid_basket]) is not None:
            best_ask_components = 2*best_ask_baguette + 4*best_ask_dip + best_ask_ukulele
            residual = best_bid_basket-best_ask_components
            assets['PICNIC_BASKET'].update_residual(residual)
            
        basket_data_ready = False    
        period = 250 # adjust
        if len(assets['PICNIC_BASKET'].residual) >= period:
            self.res_basket = np.mean(assets['PICNIC_BASKET'].residual)
            self.zscore_basket = (residual-self.res_basket)/np.std(assets['PICNIC_BASKET'].residual)
            print('ready to trade')
            basket_data_ready = True
        
        # check all data ready
        if basket_data_ready:
            #redem is short basket long components
            
            threshold = 8 # was 6
            spread = best_ask_basket-best_bid_basket
            #residual strat
            if spread <= threshold:
                
                # sell signal
                if self.zscore_basket >= self.zscore_high:
                    # SELL basket BUY components baguette dip ukulele 2:4:1
                    #component vol is of ukuleles
                    print('SHORT')
                    component_volume  = min(np.floor(-best_ask_volume_baguette/2),  np.floor(-best_ask_volume_dip/4), -best_ask_volume_ukulele)
                    component_volume_lim = min(assets['BAGUETTE'].limit - position_baguette,
                                               assets['DIP'].limit - position_dip,
                                               assets['UKULELE'].limit - position_ukulele)
                    bid_volume = min(component_volume, component_volume_lim)
                    ask_volume = min(best_bid_volume_basket, assets['PICNIC_BASKET'].limit + position_basket)
                    basket_order_size = np.floor(min(bid_volume, ask_volume))
                    print(basket_order_size)
                    # trade possible if size is positive
                    if basket_order_size > 0:
                        print("BUY BAGUETTE", str(2*basket_order_size) + "x", best_ask_baguette)
                        orders_baguette.append(Order('BAGUETTE', best_ask_baguette, 2*basket_order_size))
                        print("BUY DIP", str(4*basket_order_size) + "x", best_ask_dip)
                        orders_dip.append(Order('DIP', best_ask_dip, 4*basket_order_size))
                        print("BUY UKULELE", str(basket_order_size) + "x", best_ask_ukulele)
                        orders_ukulele.append(Order('UKULELE', best_ask_ukulele, basket_order_size))
                        print("SELL PICNIC_BASKET", str(basket_order_size) + "x", best_bid_basket)
                        orders_basket.append(Order('PICNIC_BASKET', best_bid_basket, -basket_order_size))
                # buy signal
                elif self.zscore_basket <= -self.zscore_high:
                    # BUY basket SELL components baguette dip ukulele 2:4:1
                    #component vol is of ukuleles
                    component_volume  = min(np.floor(best_bid_volume_baguette/2),  np.floor(best_bid_volume_dip/4), best_bid_volume_ukulele)
                    component_volume_lim = min(assets['BAGUETTE'].limit + position_baguette,
                                               assets['DIP'].limit + position_dip,
                                               assets['UKULELE'].limit + position_ukulele)
                    bid_volume = min(-best_ask_volume_basket, assets['PICNIC_BASKET'].limit - position_basket)
                    ask_volume = min(component_volume, component_volume_lim)
                    basket_order_size = np.floor(min(bid_volume, ask_volume))
                    # trade possible if size is positive
                    if basket_order_size > 0:
                        print("SELL BAGUETTE", str(2*basket_order_size) + "x", best_bid_baguette)
                        orders_baguette.append(Order('BAGUETTE', best_bid_baguette, -2*basket_order_size))
                        print("SELL DIP", str(4*basket_order_size) + "x", best_bid_dip)
                        orders_dip.append(Order('DIP', best_bid_dip, -4*basket_order_size))
                        print("SELL UKULELE", str(basket_order_size) + "x", best_bid_ukulele)
                        orders_ukulele.append(Order('UKULELE', best_bid_ukulele, -basket_order_size))
                        print("BUY PICNIC_BASKET", str(basket_order_size) + "x", best_ask_basket)
                        orders_basket.append(Order('PICNIC_BASKET', best_ask_basket, basket_order_size))
            
            # Add all the above orders to the result dict
            result["BAGUETTE"] = orders_baguette
            result["DIP"] = orders_dip
            result["UKULELE"] = orders_ukulele
            result["PICNIC_BASKET"] = orders_basket
            print(f'Position in basket: {position_basket}')
        # Return the dict of orders
        return result