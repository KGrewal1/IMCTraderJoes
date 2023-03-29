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
            }
        self.asset_dicts = assets
        self.printing = printing
        self.position = {"PEARLS": 0, "BANANAS": 0,
                    "COCONUTS": 0, "PINA_COLADAS": 0}
        self.short_both = False
        self.long_both = False
        self.short_spread = False
        self.long_spread = False
        self.resMA = []
        self.zscore = None
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
        # hedge ratio COCO/PINA optimum calculated 1.87
        hedge_ratio = 1.875
        # Iterate over all the keys (the available products) contained in the order depths

        for product in state.position.keys():
            self.position[product] = state.position[product]

        # Pair trading COCONUTS and PINA_COLADAS
        orders_coconut: list[Order] = []
        orders_pina: list[Order] = []
        order_depth_coconut = state.order_depths["COCONUTS"]
        best_ask_coconut, best_ask_volume_coconut, best_bid_coconut, best_bid_volume_coconut, mid_coconut = self.get_data(
            order_depth_coconut)
        assets['COCONUTS'].update_ask_prices(best_ask_coconut)
        assets['COCONUTS'].update_bid_prices(best_bid_coconut)
        order_depth_pina = state.order_depths["PINA_COLADAS"]
        best_ask_pina, best_ask_volume_pina, best_bid_pina, best_bid_volume_pina, mid_pina = self.get_data(
            order_depth_pina)
        assets["PINA_COLADAS"].update_ask_prices(best_ask_pina)
        assets["PINA_COLADAS"].update_bid_prices(best_bid_pina)
        data_ready = False

        period = 25 # adjust
        weights = np.linspace(1, period, num = period)
        if len(assets['COCONUTS'].ask_prices) >= period:
            coco_mids = (np.array(assets['COCONUTS'].ask_prices[-period:])+np.array(assets['COCONUTS'].bid_prices[-period:]))/2
            cocoMA = np.average(coco_mids, weights = weights)
            coco_std = np.sqrt(np.average((coco_mids-cocoMA)**2, weights=weights))
            pina_mids = (np.array(assets['PINA_COLADAS'].ask_prices[-period:])+np.array(assets['PINA_COLADAS'].bid_prices[-period:]))/2
            pinaMA = np.average(pina_mids, weights = weights)
            pina_std = np.sqrt(np.average((pina_mids-pinaMA)**2, weights=weights))
            print('ready to trade')
            data_ready = True


        factor = 2.5
        factor_r = 2
        if data_ready:
            # entry signal LONG overall
            if (mid_coconut >= cocoMA+factor*coco_std) and (mid_pina >= pinaMA+factor*pina_std) and not self.long_both: # 1
                self.long_both = True
                self.short_both = False
                self.long_spread = False
                self.short_spread = False
                # Breaking into an uptrend
                print('standard deviations')
                print(coco_std, pina_std)
                bid_product_1 = "COCONUTS"
                bid_product_2 = "PINA_COLADAS"
                bid_volume_1 = min(-best_ask_volume_coconut, (assets[bid_product_1].limit - self.position[bid_product_1]))
                bid_volume_2 = min(-best_ask_volume_pina, (assets[bid_product_2].limit - self.position[bid_product_2]))
                # pina_order_size = np.floor(min(bid_volume/hedge_ratio, ask_volume))
                # trade possible if size is positive
                if bid_volume_1 > 0 or bid_volume_2>0:
                    print('Long BOTH')
                    print(pinaMA, ' ', cocoMA)
                    print('mids: ', mid_pina, ' ', mid_coconut)
                    print("BUY", bid_product_1, str(bid_volume_1) + "x", best_ask_coconut)
                    orders_coconut.append(Order(bid_product_1, best_ask_coconut, bid_volume_1))
                    print("BUY", bid_product_2, str(bid_volume_2) + "x", best_ask_pina)
                    orders_pina.append(Order(bid_product_2, best_ask_pina, bid_volume_2))
                print(bid_volume_1, bid_volume_2)

            # entry signal SHORT overall
            elif (mid_coconut <= cocoMA-factor*coco_std) and (mid_pina <= pinaMA-factor*pina_std) and not self.short_both: #
                self.long_both = False
                self.short_both = True
                self.long_spread = False
                self.short_spread = False
                # Breaking into a downtrend
                print('standard deviations')
                print(coco_std, pina_std)
                ask_product_1 = "COCONUTS"
                ask_product_2 = "PINA_COLADAS"
                ask_volume_1 = min(best_bid_volume_coconut, (assets[ask_product_1].limit + self.position[ask_product_1]))
                ask_volume_2 = min(best_bid_volume_pina, (assets[ask_product_2].limit + self.position[ask_product_2]))
                # pina_order_size = np.floor(min(bid_volume/hedge_ratio, ask_volume))
                # trade possible if size is positive
                if ask_volume_1 > 0 or ask_volume_2>0:
                    print('Short BOTH')
                    print(pinaMA, ' ', cocoMA)
                    print('mids: ', mid_pina, ' ', mid_coconut)
                    print("SELL", ask_product_1, str(ask_volume_1) + "x", best_bid_coconut)
                    orders_coconut.append(Order(ask_product_1, best_bid_coconut, -ask_volume_1))
                    print("SELL", ask_product_2, str(ask_volume_2) + "x", best_bid_pina)
                    orders_pina.append(Order(ask_product_2, best_bid_pina, -ask_volume_2))
            # entry signal SHORT res
            elif (mid_coconut >= cocoMA+factor_r*coco_std) and (mid_pina <= pinaMA-factor_r*pina_std) and not self.long_spread: # 1
                self.long_both = False
                self.short_both = False
                self.long_spread = True
                self.short_spread = False
                # if coconuts high and pc low bet, short coconuts, long pc
                bid_product = "COCONUTS"
                ask_product = "PINA_COLADAS"
                bid_volume = min(-best_ask_volume_coconut, (assets[bid_product].limit - self.position[bid_product]))
                ask_volume = min(best_bid_volume_pina, (assets[ask_product].limit + self.position[ask_product]))
                # trade possible if size is positive
                if (ask_volume > 0) or (bid_volume > 0):
                    print('Short coco, long pina')
                    print('mids: ', mid_pina, ' ', mid_coconut)
                    print("BUY", bid_product, str(bid_volume) + "x", best_ask_coconut)
                    orders_coconut.append(Order(bid_product, best_ask_coconut, bid_volume))
                    print("SELL", ask_product, str(ask_volume) + "x", best_bid_pina)
                    orders_pina.append(Order(ask_product, best_bid_pina, -ask_volume))
            #entry signal LONG res
            elif (mid_coconut <= cocoMA-factor_r*coco_std) and (mid_pina >= pinaMA+factor_r*pina_std) and not self.short_spread: # 1
                self.long_both = False
                self.short_both = False
                self.long_spread = False
                self.short_spread = True
                # SELL COCONUT overpriced, BUY PINA underpriced,
                # self.long = True #allow multiple trades
                # self.short = False
                bid_product = "PINA_COLADAS"
                ask_product = "COCONUTS"
                bid_volume = min(-best_ask_volume_pina, (assets[bid_product].limit - self.position[bid_product]))
                ask_volume = min(best_bid_volume_coconut, (assets[ask_product].limit + self.position[ask_product]))
                if (ask_volume > 0) or (bid_volume > 0):
                    print('Long coco, short pina')
                    print("BUY", bid_product, str(bid_volume) + "x", best_ask_pina)
                    orders_pina.append(Order(bid_product, best_ask_pina, bid_volume))
                    print("SELL", ask_product, str(ask_volume) + "x", best_bid_coconut)
                    orders_coconut.append(Order(ask_product, best_bid_coconut, -ask_volume))

            elif self.long_both: # 1
                # Breaking into an uptrend
                print('standard deviations')
                print(coco_std, pina_std)
                bid_product_1 = "COCONUTS"
                bid_product_2 = "PINA_COLADAS"
                bid_volume_1 = min(-best_ask_volume_coconut, (assets[bid_product_1].limit - self.position[bid_product_1]))
                bid_volume_2 = min(-best_ask_volume_pina, (assets[bid_product_2].limit - self.position[bid_product_2]))
                # pina_order_size = np.floor(min(bid_volume/hedge_ratio, ask_volume))
                # trade possible if size is positive
                if bid_volume_1 > 0 or bid_volume_2>0:
                    print('finishing order')
                    print('Long BOTH')
                    print(pinaMA, ' ', cocoMA)
                    print('mids: ', mid_pina, ' ', mid_coconut)
                    print("BUY", bid_product_1, str(bid_volume_1) + "x", best_ask_coconut)
                    orders_coconut.append(Order(bid_product_1, best_ask_coconut, bid_volume_1))
                    print("BUY", bid_product_2, str(bid_volume_2) + "x", best_ask_pina)
                    orders_pina.append(Order(bid_product_2, best_ask_pina, bid_volume_2))
                print(bid_volume_1, bid_volume_2)

            # entry signal SHORT overall
            elif self.short_both: #
                # Breaking into a downtrend
                print('standard deviations')
                print(coco_std, pina_std)
                ask_product_1 = "COCONUTS"
                ask_product_2 = "PINA_COLADAS"
                ask_volume_1 = min(best_bid_volume_coconut, (assets[ask_product_1].limit + self.position[ask_product_1]))
                ask_volume_2 = min(best_bid_volume_pina, (assets[ask_product_2].limit + self.position[ask_product_2]))
                # pina_order_size = np.floor(min(bid_volume/hedge_ratio, ask_volume))
                # trade possible if size is positive
                if ask_volume_1 > 0 or ask_volume_2>0:
                    print('finishing order')
                    print('Short BOTH')
                    print(pinaMA, ' ', cocoMA)
                    print('mids: ', mid_pina, ' ', mid_coconut)
                    print("SELL", ask_product_1, str(ask_volume_1) + "x", best_bid_coconut)
                    orders_coconut.append(Order(ask_product_1, best_bid_coconut, -ask_volume_1))
                    print("SELL", ask_product_2, str(ask_volume_2) + "x", best_bid_pina)
                    orders_pina.append(Order(ask_product_2, best_bid_pina, -ask_volume_2))
            # entry signal SHORT res
            elif self.long_spread: # 1
                # if coconuts high and pc low bet, short coconuts, long pc
                bid_product = "COCONUTS"
                ask_product = "PINA_COLADAS"
                bid_volume = min(-best_ask_volume_coconut, (assets[bid_product].limit - self.position[bid_product]))
                ask_volume = min(best_bid_volume_pina, (assets[ask_product].limit + self.position[ask_product]))
                # trade possible if size is positive
                if (ask_volume > 0) or (bid_volume > 0):
                    print('finishing order')
                    print('Short coco, long pina')
                    print('mids: ', mid_pina, ' ', mid_coconut)
                    print("BUY", bid_product, str(bid_volume) + "x", best_ask_coconut)
                    orders_coconut.append(Order(bid_product, best_ask_coconut, bid_volume))
                    print("SELL", ask_product, str(ask_volume) + "x", best_bid_pina)
                    orders_pina.append(Order(ask_product, best_bid_pina, -ask_volume))
            #entry signal LONG res
            elif self.short_spread: # 1
                # SELL COCONUT overpriced, BUY PINA underpriced,
                # self.long = True #allow multiple trades
                # self.short = False
                bid_product = "PINA_COLADAS"
                ask_product = "COCONUTS"
                bid_volume = min(-best_ask_volume_pina, (assets[bid_product].limit - self.position[bid_product]))
                ask_volume = min(best_bid_volume_coconut, (assets[ask_product].limit + self.position[ask_product]))
                if (ask_volume > 0) or (bid_volume > 0):
                    print('finishing order')
                    print('Long coco, short pina')
                    print("BUY", bid_product, str(bid_volume) + "x", best_ask_pina)
                    orders_pina.append(Order(bid_product, best_ask_pina, bid_volume))
                    print("SELL", ask_product, str(ask_volume) + "x", best_bid_coconut)
                    orders_coconut.append(Order(ask_product, best_bid_coconut, -ask_volume))

            # exit signal for long trades
            # elif self.long and delta >= -delta_out:
            #     print('Exiting long: ', delta)
            #     print(f'res (bid, mid, ask) ({synth_bid}, {res}, {synth_ask})')
            #     print('mids: ', mid_pina, ' ', mid_coconut)
            #     self.long = False
            #     product = "COCONUTS"
            #     volume = self.position["COCONUTS"]
            #     if volume > 0:
            #         # sell all existing positions
            #         print("Exit SELL", product, str(volume) + "x", best_bid_coconut)
            #         orders_coconut.append(Order(product, best_bid_coconut, -volume))
            #     elif volume < 0:
            #         # buy out all existing positions
            #         print("Exit BUY", product, str(-volume) + "x", best_ask_coconut)
            #         orders_coconut.append(Order(product, best_ask_coconut, -volume))

            #     product = "PINA_COLADAS"
            #     volume = self.position["PINA_COLADAS"]
            #     if volume > 0:
            #         # sell all existing positions
            #         print("Exit SELL", product, str(volume) + "x", best_bid_pina)
            #         orders_pina.append(Order(product, best_bid_pina, -volume))
            #     elif volume < 0:
            #         # buy out all existing positions
            #         print("Exit BUY", product, str(-volume) + "x", best_ask_pina)
            #         orders_pina.append(Order(product, best_ask_pina, -volume))

            # exit signal for short trades
            # elif self.short and delta <= delta_out:
            #     print('Exiting short: delta:', delta)
            #     print(f'res (bid, mid, ask) ({synth_bid}, {res}, {synth_ask})')
            #     print('mids: ', mid_pina, ' ', mid_coconut)
            #     self.short = False
            #     product = "COCONUTS"
            #     volume = self.position["COCONUTS"]
            #     if volume > 0:
            #         # sell all existing positions
            #         print("Exit SELL", product, str(volume) + "x", best_bid_coconut)
            #         orders_coconut.append(Order(product, best_bid_coconut, -volume))
            #     elif volume < 0:
            #         # buy out all existing positions
            #         print("Exit BUY", product, str(-volume) + "x", best_ask_coconut)
            #         orders_coconut.append(Order(product, best_ask_coconut, -volume))

            #     product = "PINA_COLADAS"
            #     volume = self.position["PINA_COLADAS"]
            #     if volume > 0:
            #         # sell all existing positions
            #         print("Exit SELL", product, str(volume) + "x", best_bid_pina)
            #         orders_pina.append(Order(product, best_bid_pina, -volume))
            #     elif volume < 0:
            #         # buy out all existing positions
            #         print("Exit BUY", product, str(-volume) + "x", best_ask_pina)
            #         orders_pina.append(Order(product, best_ask_pina, -volume))
            print('Pos_pina:', self.position['PINA_COLADAS'])
            print('Pos_coco:', self.position['COCONUTS'])

            #hedge checker
            #check polsisiotns within 1.77-2.07 hedge ratio
#             if (self.position['PINA_COLADAS'] / self.position['COCONUTS'] < hedge_ratio+0.2) and (self.position['PINA_COLADAS'] / self.position['COCONUTS'] > hedge_ratio-0.2):
#                 continue
#             else:
                #adjust so revert closer to 0,0
            #else adjust to 1.87

            # Add all the above orders to the result dict
            result["COCONUTS"] = orders_coconut
            result["PINA_COLADAS"] = orders_pina
#         if len(result) != 0:
#             print(result)
        # Return the dict of orders
        return result
