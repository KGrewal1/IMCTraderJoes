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


class MyKalmanFilter:
    """Kalman filter for trading pairs"""
    def __init__(self, delta=1e-4, R=1e-3):
        # measurement noise variance
        self.R = R

        # co-variance of process noise(2 dimensions)
        self.Q = delta / (1-delta) * np.eye(2)

        # previous state
        self.x = np.zeros((2, 1))

        # state covariance
        self.P = np.zeros((2,2))

    def step_forward(self, y1, y2):
        # Before entering the equations, let's define H as (1, 2) matrix
        H = np.array([y2, 1])[None]
        # and define z
        z = y1

        ## TIME UPDATE ##
        # first thing is to predict new state as the previous one (2x1)
        x_hat = self.x

        # then, the uncertainty or covariance prediction
        P_hat = self.P + self.Q

        ## MEASUREMENT UPDATE ##
        # calc the Kalman gain
        K = P_hat.dot(H.T)/(H.dot(P_hat.dot(H.T))+self.R)

        # state update part 1 (measurement estimation)
        z_hat = H.dot(x_hat)

        # state update part 2
        x = x_hat + K.dot(z-z_hat)

        # uncertainty update
        self.P = (np.eye(2)-K.dot(H)).dot(P_hat)

        # refresh the previous state
        self.x = x

        return x, self.P, K, z_hat

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
        self.short = False
        self.long = False
        self.resMA = []
        self.zscore = None
        self.zscore_low = -0.5 #edit
        self.zscore_high = 3
        self.mkf = MyKalmanFilter(delta=1e-4, R=1e-3)
        self.burnt_in = False

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
        mkf = self.mkf
        assets = self.asset_dicts
        # Initialize the method output dict as an empty dict
        result = {}
        # Iterate over all the keys (the available products) contained in the order depths

        for product in state.position.keys():
            self.position[product] = state.position[product]

        # Pair trading COCONUTS and PINA_COLADAS
        orders_coconut: list[Order] = []
        orders_pina: list[Order] = []
        order_depth_coconut = state.order_depths["COCONUTS"]
        best_ask_coconut, best_ask_volume_coconut, best_bid_coconut, best_bid_volume_coconut, mid_coconut = self.get_data(
            order_depth_coconut)
        order_depth_pina = state.order_depths["PINA_COLADAS"]
        best_ask_pina, best_ask_volume_pina, best_bid_pina, best_bid_volume_pina, mid_pina = self.get_data(
            order_depth_pina)
        # Calculate residuals
        if mid_coconut is not None and mid_pina is not None:
            x, _, _, z_hat = mkf.step_forward(mid_pina, mid_coconut)
            hedge_ratio = x[0].squeeze()
            self.zscore = (mid_pina - z_hat.squeeze())/1.7
        if state.timestamp==10000:
            self.burnt_in = True

        if self.burnt_in:
            # entry signal SHORT res
            if self.zscore >= self.zscore_high and not self.short: # 1
                # SELL PINA overpriced, BUY COCONUT underpriced; pina and coconut volume 1:2
                self.short = True #allow multiple trades
                bid_product = "COCONUTS"
                ask_product = "PINA_COLADAS"
                bid_volume = min(-best_ask_volume_coconut, (assets[bid_product].limit - self.position[bid_product]))
                ask_volume = min(best_bid_volume_pina, (assets[ask_product].limit + self.position[ask_product]))
                pina_order_size = np.floor(min(bid_volume/hedge_ratio, ask_volume))
                # trade possible if size is positive
                if pina_order_size > 0:
                    print('z-score:', self.zscore)
                    print('mids: ', mid_pina, ' ', mid_coconut)
                    print("BUY", bid_product, str(np.round(hedge_ratio*pina_order_size)) + "x", best_ask_coconut)
                    orders_coconut.append(Order(bid_product, best_ask_coconut, np.round(hedge_ratio*pina_order_size)))
                    print("SELL", ask_product, str(pina_order_size) + "x", best_bid_pina)
                    orders_pina.append(Order(ask_product, best_bid_pina, -pina_order_size))
            #entry signal LONG res
            elif self.zscore <= -self.zscore_high and not self.long:
                # SELL COCONUT overpriced, BUY PINA underpriced,
                self.long = True #allow multiple trades
                bid_product = "PINA_COLADAS"
                ask_product = "COCONUTS"
                bid_volume = min(-best_ask_volume_pina, (assets[bid_product].limit - self.position[bid_product]))
                ask_volume = min(best_bid_volume_coconut, (assets[ask_product].limit + self.position[ask_product]))
                pina_order_size = np.floor(min(bid_volume, ask_volume/hedge_ratio))
                # TODO: TREAT VOLUME SEPARATELY?
                if pina_order_size > 0:
                    print('z-score:', self.zscore)
                    print('mids: ', mid_pina, ' ', mid_coconut)
                    print("BUY", bid_product, str(pina_order_size) + "x", best_ask_pina)
                    orders_pina.append(Order(bid_product, best_ask_pina, pina_order_size))
                    print("SELL", ask_product, str(np.round(hedge_ratio*pina_order_size)) + "x", best_bid_coconut)
                    orders_coconut.append(Order(ask_product, best_bid_coconut, -np.round(hedge_ratio*pina_order_size)))
            # exit signal for long trades
            elif self.long and self.zscore >= -self.zscore_low:
                print('z-score:', self.zscore)
                print('mids: ', mid_pina, ' ', mid_coconut)
                self.long = False
                product = "COCONUTS"
                volume = self.position["COCONUTS"]
                if volume > 0:
                    # sell all existing positions
                    print("Exit SELL", product, str(volume) + "x", best_bid_coconut)
                    orders_coconut.append(Order(product, best_bid_coconut, -volume))
                elif volume < 0:
                    # buy out all existing positions
                    print("Exit BUY", product, str(-volume) + "x", best_ask_coconut)
                    orders_coconut.append(Order(product, best_ask_coconut, -volume))

                product = "PINA_COLADAS"
                volume = self.position["PINA_COLADAS"]
                if volume > 0:
                    # sell all existing positions
                    print("Exit SELL", product, str(volume) + "x", best_bid_pina)
                    orders_pina.append(Order(product, best_bid_pina, -volume))
                elif volume < 0:
                    # buy out all existing positions
                    print("Exit BUY", product, str(-volume) + "x", best_ask_pina)
                    orders_pina.append(Order(product, best_ask_pina, -volume))

            # exit signal for short trades
            elif self.short and self.zscore <= self.zscore_low:
                print('z-score:', self.zscore)
                print('mids: ', mid_pina, ' ', mid_coconut)
                self.short = False
                product = "COCONUTS"
                volume = self.position["COCONUTS"]
                if volume > 0:
                    # sell all existing positions
                    print("Exit SELL", product, str(volume) + "x", best_bid_coconut)
                    orders_coconut.append(Order(product, best_bid_coconut, -volume))
                elif volume < 0:
                    # buy out all existing positions
                    print("Exit BUY", product, str(-volume) + "x", best_ask_coconut)
                    orders_coconut.append(Order(product, best_ask_coconut, -volume))

                product = "PINA_COLADAS"
                volume = self.position["PINA_COLADAS"]
                if volume > 0:
                    # sell all existing positions
                    print("Exit SELL", product, str(volume) + "x", best_bid_pina)
                    orders_pina.append(Order(product, best_bid_pina, -volume))
                elif volume < 0:
                    # buy out all existing positions
                    print("Exit BUY", product, str(-volume) + "x", best_ask_pina)
                    orders_pina.append(Order(product, best_ask_pina, -volume))
            # elif -self.zscore_low < self.zscore < self.zscore_low:
            #     self.long = False
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
