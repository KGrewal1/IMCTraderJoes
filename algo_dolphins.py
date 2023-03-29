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
# asset class: stores info about an asset not in the datamodel
class Asset:
    """asset class to contain previous prices, and the limits for an asset"""
    def __init__(self, limit, period, fast_period):
        self.limit = limit
        self.ask_prices = []
        self.bid_prices = []
        self.residual = []
        self.last_mid = None
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
        """update the period most recent bid prices"""
        if len(self.bid_prices)<self.period:
            self.bid_prices.append(bid_price)
        else:
            self.bid_prices.pop(0)
            self.bid_prices.append(bid_price)

    def update_residual(self, res):
        """update the most recent residuals"""
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
                "DIVING_GEAR":Asset(50, 670, 10),
            }
        self.asset_dicts = assets
        self.printing = printing
        self.position = {"PEARLS": 0, "BANANAS": 0,
                    "COCONUTS": 0, "PINA_COLADAS": 0, 'DIVING_GEAR': 0}
        self.last_obs = None
        self.buy_gear = False
        self.sell_gear = False

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
        order_depth_gear = state.order_depths["DIVING_GEAR"]
        best_ask_gear, best_ask_volume_gear, best_bid_gear, best_bid_volume_gear, _, all_asks, all_bids = self.get_data(order_depth_gear)
        # Initialize the method output dict as an empty dict
        result = {}
        orders_gear: list[Order] = []

        for product in state.position.keys():
            self.position[product] = state.position[product]
        observations = state.observations
        if self.last_obs is None:
            delta = 0
            self.last_obs = observations
        else:
            delta = observations-self.last_obs
            self.last_obs = observations
        print(delta)
        if delta>=5 or self.buy_gear:
            self.buy_gear = True
            self.sell_gear = False
            print('spike up')
            print('buy diving gear')
            bid_product = "DIVING_GEAR"
            print(best_ask_gear)
            print(all_asks)
            order_size = min(-best_ask_volume_gear, assets[bid_product].limit - self.position[bid_product])
            if order_size>0:
                print("BUY", bid_product, str(order_size) + "x", best_ask_gear)
                orders_gear.append(Order(bid_product, best_ask_gear, order_size))
                try:
                    second_vol = order_depth_gear.sell_orders[all_asks[1]]
                    second_order_size = min(-second_vol, assets[bid_product].limit - self.position[bid_product]-order_size)
                    print("BUY", bid_product, str(second_order_size) + "x", all_asks[1])
                    orders_gear.append(Order(bid_product, all_asks[1], second_order_size))
                except: pass
            else:
                self.sell_gear = False
                self.buy_gear = False
            print(delta)
        if delta<= -5 or self.sell_gear:
            self.sell_gear = True
            self.buy_gear = False
            print('spike down')
            print('sell diving gear')
            ask_product = "DIVING_GEAR"
            print(best_bid_gear)
            print(all_bids)
            order_size = min(best_bid_volume_gear,assets[ask_product].limit + self.position[ask_product])
            if order_size>0:
                print("SELL", ask_product, str(order_size) + "x", best_bid_gear)
                orders_gear.append(Order(ask_product, best_bid_gear, -order_size))
                try:
                    second_vol = order_depth_gear.buy_orders[all_bids[1]]
                    second_order_size = min(second_vol,assets[ask_product].limit + self.position[ask_product]-order_size)
                    print("SELL", ask_product, str(second_order_size) + "x", all_bids[1])
                    orders_gear.append(Order(ask_product, all_bids[1], -second_order_size))
                except: pass
            else:
                self.sell_gear = False
                self.buy_gear = False
            print(delta)
        result["DIVING_GEAR"] = orders_gear

        # Pair trading COCONUTS and PINA_COLADAS
#         orders_coconut: list[Order] = []
#         orders_pina: list[Order] = []
#         order_depth_coconut = state.order_depths["COCONUTS"]
#         best_ask_coconut, best_ask_volume_coconut, best_bid_coconut, best_bid_volume_coconut, mid_coconut = self.get_data(
#             order_depth_coconut)
#         order_depth_pina = state.order_depths["PINA_COLADAS"]
#         best_ask_pina, best_ask_volume_pina, best_bid_pina, best_bid_volume_pina, mid_pina = self.get_data(
#             order_depth_pina)
#         data_ready = False
#         # Calculate residuals
#         if mid_coconut is not None and mid_pina is not None:
#             res = mid_pina - hedge_ratio * mid_coconut
#             assets['COCONUTS'].update_residual(res)

#         period = 670 # adjust
#         if len(assets['COCONUTS'].residual) >= period:
#             self.resMA = np.mean(assets['COCONUTS'].residual[-period:])
#             self.zscore = (res-self.resMA)/np.std(assets['COCONUTS'].residual[-period:])
#             print('ready to trade')
#             data_ready = True

#         if data_ready:
#             # entry signal SHORT res
#             if self.zscore >= self.zscore_high and not self.short and not self.long: # 1
#                 # SELL PINA overpriced, BUY COCONUT underpriced; pina and coconut volume 1:2
#                 self.short = True #allow multiple trades
#                 bid_product = "COCONUTS"
#                 ask_product = "PINA_COLADAS"
#                 bid_volume = min(-best_ask_volume_coconut, (assets[bid_product].limit - self.position[bid_product]))
#                 ask_volume = min(best_bid_volume_pina, (assets[ask_product].limit + self.position[ask_product]))
#                 pina_order_size = np.floor(min(bid_volume/hedge_ratio, ask_volume))
#                 # trade possible if size is positive
#                 if pina_order_size > 0:
#                     print('z-score:', self.zscore)
#                     print('mids: ', mid_pina, ' ', mid_coconut)
#                     print("BUY", bid_product, str(hedge_ratio*pina_order_size) + "x", best_ask_coconut)
#                     orders_coconut.append(Order(bid_product, best_ask_coconut, np.round(hedge_ratio*pina_order_size)))
#                     print("SELL", ask_product, str(pina_order_size) + "x", best_bid_pina)
#                     orders_pina.append(Order(ask_product, best_bid_pina, -pina_order_size))
#             #entry signal LONG res
#             elif self.zscore <= -self.zscore_high and not self.long and not self.short:
#                 # SELL COCONUT overpriced, BUY PINA underpriced,
#                 self.long = True #allow multiple trades
#                 bid_product = "PINA_COLADAS"
#                 ask_product = "COCONUTS"
#                 bid_volume = min(-best_ask_volume_pina, (assets[bid_product].limit - self.position[bid_product]))
#                 ask_volume = min(best_bid_volume_coconut, (assets[ask_product].limit + self.position[ask_product]))
#                 pina_order_size = np.floor(min(bid_volume, ask_volume/hedge_ratio))
#                 # TODO: TREAT VOLUME SEPARATELY?
#                 if pina_order_size > 0:
#                     print('z-score:', self.zscore)
#                     print('mids: ', mid_pina, ' ', mid_coconut)
#                     print("BUY", bid_product, str(pina_order_size) + "x", best_ask_pina)
#                     orders_pina.append(Order(bid_product, best_ask_pina, pina_order_size))
#                     print("SELL", ask_product, str(hedge_ratio*pina_order_size) + "x", best_bid_coconut)
#                     orders_coconut.append(Order(ask_product, best_bid_coconut, -np.round(hedge_ratio*pina_order_size)))

#             # exit signal for long trades
#             elif self.long and self.zscore >= -self.zscore_low:
#                 print('Exiting long: z-score:', self.zscore)
#                 print('mids: ', mid_pina, ' ', mid_coconut)
#                 self.long = False
#                 product = "COCONUTS"
#                 volume = self.position["COCONUTS"]
#                 if volume > 0:
#                     # sell all existing positions
#                     print("Exit SELL", product, str(volume) + "x", best_bid_coconut)
#                     orders_coconut.append(Order(product, best_bid_coconut, -volume))
#                 elif volume < 0:
#                     # buy out all existing positions
#                     print("Exit BUY", product, str(-volume) + "x", best_ask_coconut)
#                     orders_coconut.append(Order(product, best_ask_coconut, -volume))

#                 product = "PINA_COLADAS"
#                 volume = self.position["PINA_COLADAS"]
#                 if volume > 0:
#                     # sell all existing positions
#                     print("Exit SELL", product, str(volume) + "x", best_bid_pina)
#                     orders_pina.append(Order(product, best_bid_pina, -volume))
#                 elif volume < 0:
#                     # buy out all existing positions
#                     print("Exit BUY", product, str(-volume) + "x", best_ask_pina)
#                     orders_pina.append(Order(product, best_ask_pina, -volume))

#             # exit signal for short trades
#             elif self.short and self.zscore <= self.zscore_low:
#                 print('Exiting short: z-score:', self.zscore)
#                 print('mids: ', mid_pina, ' ', mid_coconut)
#                 self.short = False
#                 product = "COCONUTS"
#                 volume = self.position["COCONUTS"]
#                 if volume > 0:
#                     # sell all existing positions
#                     print("Exit SELL", product, str(volume) + "x", best_bid_coconut)
#                     orders_coconut.append(Order(product, best_bid_coconut, -volume))
#                 elif volume < 0:
#                     # buy out all existing positions
#                     print("Exit BUY", product, str(-volume) + "x", best_ask_coconut)
#                     orders_coconut.append(Order(product, best_ask_coconut, -volume))

#                 product = "PINA_COLADAS"
#                 volume = self.position["PINA_COLADAS"]
#                 if volume > 0:
#                     # sell all existing positions
#                     print("Exit SELL", product, str(volume) + "x", best_bid_pina)
#                     orders_pina.append(Order(product, best_bid_pina, -volume))
#                 elif volume < 0:
#                     # buy out all existing positions
#                     print("Exit BUY", product, str(-volume) + "x", best_ask_pina)
#                     orders_pina.append(Order(product, best_ask_pina, -volume))
#             print('Pos_pina:', self.position['PINA_COLADAS'])
#             print('Pos_coco:', self.position['COCONUTS'])

#             #hedge checker
#             #check polsisiotns within 1.77-2.07 hedge ratio
# #             if (self.position['PINA_COLADAS'] / self.position['COCONUTS'] < hedge_ratio+0.2) and (self.position['PINA_COLADAS'] / self.position['COCONUTS'] > hedge_ratio-0.2):
# #                 continue
# #             else:
#                 #adjust so revert closer to 0,0
#             #else adjust to 1.87

#             # Add all the above orders to the result dict
#             result["COCONUTS"] = orders_coconut
#             result["PINA_COLADAS"] = orders_pina
        # if len(result) != 0:
        #     print(result)
        # Return the dict of orders
        return result
