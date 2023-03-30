"""
The python module to be uploaded to the website, with the algorithmic trading logic
The log tracks all print commands
coco-pina pairs no early exit (can change to some early exit)
"""

import numpy as np
from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order

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
            }
        self.asset_dicts = assets
        self.printing = printing
        self.position = {"PEARLS": 0, "BANANAS": 0,
                    "COCONUTS": 0, "PINA_COLADAS": 0}
        #coco-pina
        self.short = False
        self.long = False
        self.resMA = []
        self.zscore = 0
        self.zscore_high = 2.4 #2.5 gave average of 35k over days 1,2,3
        self.count = 0
        self.exit = 0

    def get_data(self, order_depth):
        if len(order_depth.sell_orders) > 0:
            asks = sorted(order_depth.sell_orders.keys())
            best_ask = asks[0]
            best_ask_volume = order_depth.sell_orders[best_ask]
        if len(order_depth.buy_orders) != 0:
            bids = sorted(order_depth.buy_orders.keys(), reverse=True)
            best_bid = bids[0]
            best_bid_volume = order_depth.buy_orders[best_bid]
            mid = (best_ask+best_bid)/2
        return best_ask, best_ask_volume, best_bid, best_bid_volume, mid, asks, bids

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        assets = self.asset_dicts
        # Initialize the method output dict as an empty dict
        result = {}
        # hedge ratio COCO/PINA optimum calculated 1.87
        hedge_ratio = 1.875
        # Iterate over all the keys (the available products) contained in the order depths

        for product in state.position.keys():
            self.position[product] = state.position[product]

        # STRAT 3 pairs trading COCONUTS and PINA_COLADAS
        orders_coconut: list[Order] = []
        orders_pina: list[Order] = []
        order_depth_coconut = state.order_depths["COCONUTS"]
        best_ask_coconut, best_ask_volume_coconut, best_bid_coconut, best_bid_volume_coconut, mid_coconut, all_ask_coconut, all_bid_coconut = self.get_data(
            order_depth_coconut)
        position_coconut = state.position.get('COCONUTS', 0)
        order_depth_pina = state.order_depths["PINA_COLADAS"]
        best_ask_pina, best_ask_volume_pina, best_bid_pina, best_bid_volume_pina, mid_pina, all_ask_pina, all_bid_pina = self.get_data(
            order_depth_pina)
        position_pina = state.position.get('PINA_COLADAS', 0)
        data_ready = False
        # Calculate residuals
        if mid_coconut is not None and mid_pina is not None:
            res = mid_pina - hedge_ratio * mid_coconut
            assets['COCONUTS'].update_residual(res)

        period = 670 # adjust
        if len(assets['COCONUTS'].residual) >= period:
            self.resMA = np.mean(assets['COCONUTS'].residual)
            # self.last_zscore = self.zscore
            self.zscore = (res-self.resMA)/np.std(assets['COCONUTS'].residual)
            print('ready to trade')
            data_ready = True

        if data_ready:
            # entry signal SHORT res
            if self.zscore >= self.zscore_high and not self.short: # and self.zscore<self.last_zscore:
                self.count+=1
                # SELL PINA overpriced, BUY COCONUT underpriced; pina and coconut volume 1:2
                #self.short = True   # allow multiple trades
                bid_product = "COCONUTS"
                ask_product = "PINA_COLADAS"
                bid_volume = min(-best_ask_volume_coconut, assets[bid_product].limit - position_coconut)
                ask_volume = min(best_bid_volume_pina, assets[ask_product].limit + position_pina)
                max_available = np.floor(min(bid_volume/hedge_ratio, ask_volume)) #max avaialable
                pina_order_size = min(50, max_available)
                if abs(position_pina)<assets['PINA_COLADAS'].limit and pina_order_size == 0:
                    pina_order_size = min(5, assets['PINA_COLADAS'].limit-abs(position_pina))
                # trade possible if size is positive and spread not too big
                spread = max(best_ask_pina-best_bid_pina, best_ask_coconut-best_bid_coconut)
                spread_coconut = best_ask_coconut-best_bid_coconut
                if pina_order_size > 0 and spread_coconut <= 2:
                    print("BUY", bid_product, str(hedge_ratio*pina_order_size) + "x", best_ask_coconut)
                    orders_coconut.append(Order(bid_product, best_ask_coconut, np.round(hedge_ratio*pina_order_size)))
                    print("SELL", ask_product, str(pina_order_size) + "x", best_bid_pina)
                    orders_pina.append(Order(ask_product, best_bid_pina, -pina_order_size))
            #entry signal LONG res
            elif self.zscore <= -self.zscore_high and not self.long: # and self.zscore>self.last_zscore:
                self.count+=1
                # SELL COCONUT overpriced, BUY PINA underpriced,
                #self.long = True   # allow multiple trades
                bid_product = "PINA_COLADAS"
                ask_product = "COCONUTS"
                bid_volume = min(-best_ask_volume_pina, assets[bid_product].limit - position_pina)
                ask_volume = min(best_bid_volume_coconut, assets[ask_product].limit + position_coconut)
                max_available = np.floor(min(bid_volume, ask_volume/hedge_ratio))
                pina_order_size = min(50, max_available)
                if abs(position_pina)<assets['PINA_COLADAS'].limit and pina_order_size == 0:
                    pina_order_size = min(5, assets['PINA_COLADAS'].limit-abs(position_pina))
                # trade possible if size is positive
                spread = max(best_ask_pina-best_bid_pina, best_ask_coconut-best_bid_coconut)
                spread_coconut = best_ask_coconut-best_bid_coconut
                if pina_order_size > 0 and spread_coconut <= 2:
                    print("BUY", bid_product, str(pina_order_size) + "x", best_ask_pina)
                    orders_pina.append(Order(bid_product, best_ask_pina, pina_order_size))
                    print("SELL", ask_product, str(hedge_ratio*pina_order_size) + "x", best_bid_coconut)
                    orders_coconut.append(Order(ask_product, best_bid_coconut, -np.round(hedge_ratio*pina_order_size)))

            print('Pos_pina:', position_pina)
            print('Pos_coco:', position_coconut)

            # Add all the above orders to the result dict
            result["COCONUTS"] = orders_coconut
            result["PINA_COLADAS"] = orders_pina

        # Return the dict of orders
        print(f'count: {self.count}, exit: {self.exit}')
        return result
