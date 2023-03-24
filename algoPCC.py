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
    if abs(np.floor((max_limit/30)*(1-(sellers*pos/max_limit*buyers)))) > abs(0.75*max_limit - pos):
        return abs(0.75*max_limit - pos)
    else:
        return abs(np.floor((max_limit/30)*(1-(sellers*pos/max_limit*buyers))))
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
                "COCONUTS":Asset(600, 10, 10),
                "PINA_COLADAS":Asset(300, 10, 5),
            }
        self.asset_dicts = assets
        self.printing = printing
        self.last_trade_time = 0
        self.last_trade = (0,0) # tuple of PC, C :UNSIGNED
        self.last_trade_volume = (0,0) # tuple of PC, C :SIGNED
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


            if product == 'PINA_COLADAS':
                # Initialize the list of Orders to be sent as an empty list
                last_trade_time = self.last_trade_time
                last_trade_PC, last_trade_C = self.last_trade
                last_trade_volume_PC, last_trade_volume_C = self.last_trade_volume
                orders_PC: list[Order] = []
                limit_PC = assets['PINA_COLADAS'].limit

                # Retrieve the Order Depth containing all the market BUY and SELL orders

                order_depth_PC: OrderDepth = state.order_depths['PINA_COLADAS']


                try:
                    position_PC = state.position['PINA_COLADAS']
                except KeyError:
                    position_PC = 0

                # If statement checks if there are any SELL orders in the BANANAS market
                if len(order_depth_PC.sell_orders) > 0:
                    best_ask_PC = min(order_depth_PC.sell_orders.keys())
                    best_ask_volume_PC = order_depth_PC.sell_orders[best_ask_PC]
                    assets['PINA_COLADAS'].update_ask_prices(best_ask_PC)

                if len(order_depth_PC.buy_orders) != 0:
                    best_bid_PC = max(order_depth_PC.buy_orders.keys())
                    best_bid_volume_PC = order_depth_PC.buy_orders[best_bid_PC]
                    assets['PINA_COLADAS'].update_bid_prices(best_bid_PC)

                mid_PC = (best_ask_PC+best_bid_PC)/2



                orders_C: list[Order] = []
                order_depth_C: OrderDepth = state.order_depths['COCONUTS']

                limit_C = assets['COCONUTS'].limit
                try:
                    position_C = state.position['COCONUTS']
                except KeyError:
                    position_C = 0

                # If statement checks if there are any SELL orders in the BANANAS market
                if len(order_depth_C.sell_orders) > 0:
                    best_ask_C = min(order_depth_C.sell_orders.keys())
                    best_ask_volume_C = order_depth_C.sell_orders[best_ask_C]
                    assets['COCONUTS'].update_ask_prices(best_ask_C)

                if len(order_depth_C.buy_orders) != 0:
                    best_bid_C = max(order_depth_C.buy_orders.keys())
                    best_bid_volume_C = order_depth_C.buy_orders[best_bid_C]
                    assets['COCONUTS'].update_bid_prices(best_bid_C)

                mid_C = (best_ask_C+best_bid_C)/2

                profit = 0
                # buying at the ask price
                if last_trade_volume_PC<0:
                    profit = profit -last_trade_volume_PC*last_trade_PC +last_trade_volume_PC*best_ask_PC

                # selling at the bid price
                if last_trade_volume_PC>0:
                    profit = profit +last_trade_volume_PC*best_bid_PC -last_trade_PC*last_trade_volume_PC

                # buying at the ask price
                if last_trade_volume_C<0:
                    profit = profit -last_trade_C*last_trade_volume_C +last_trade_volume_C*best_ask_C

                # selling at the bid price
                if last_trade_volume_C>0:
                    profit = profit +last_trade_volume_C*best_bid_C -last_trade_C*last_trade_volume_C

                profit_thresh = 100
                loss_thresh = 100
                if position_PC + position_C ==0: out_position = True
                else: out_position = False

                if profit>profit_thresh:
                    print('start profit liquidation')
                    # print('Last Trade for Pina Coladas (P,V):', last_trade_PC, last_trade_volume_PC)
                    # print('Last Trade for Coconuts (P,V):', last_trade_C, last_trade_volume_C)
                    # sell if positive position
                    if position_PC>0:
                        order_size_PC = min(best_bid_volume_PC, 0+position_PC)
                        print("SELL", 'PINA_COLADAS', str(order_size_PC) + "x", best_bid_PC)
                        orders_PC.append(Order('PINA_COLADAS', best_bid_PC, -order_size_PC))
                        position_PC = position_PC-order_size_PC
                    # buy if negative position
                    if position_PC<0:
                        order_size_PC = min(-best_ask_volume_PC, 0-position_PC)
                        print("BUY", 'PINA_COLADAS', str(order_size_PC) + "x", best_ask_PC)
                        orders_PC.append(Order('PINA_COLADAS', best_ask_PC, order_size_PC))
                        position_PC = position_PC+order_size_PC
                    # sell if posititive position
                    if position_C>0:
                        order_size_C = min(best_bid_volume_C, 0+position_C)
                        print("SELL", 'COCONUTS', str(order_size_C) + "x", best_bid_C)
                        orders_C.append(Order('COCONUTS', best_bid_C, -order_size_C))
                        position_C = position_C-order_size_C

                    # buy if negative position
                    if position_C<0:
                        order_size_C = min(-best_ask_volume_C, 0-position_C)
                        print("BUY", 'COCONUTS', str(order_size_C) + "x", best_ask_C)
                        orders_C.append(Order('COCONUTS', best_ask_C, order_size_C))
                        position_C = position_C+order_size_C
                    self.last_trade_time =0

                    self.last_trade_volume = (position_PC,position_C)
                    print('end profit liquidation')


                    if profit<-loss_thresh:
                        print('start loss liquidation')
                        # print('Last Trade for Pina Coladas (P,V):', last_trade_PC, last_trade_volume_PC)
                        # print('Last Trade for Coconuts (P,V):', last_trade_C, last_trade_volume_C)
                        # sell if positive position
                        if position_PC>0:
                            order_size_PC = min(best_bid_volume_PC, 0+position_PC)
                            print("SELL", 'PINA_COLADAS', str(order_size_PC) + "x", best_bid_PC)
                            orders_PC.append(Order('PINA_COLADAS', best_bid_PC, -order_size_PC))
                            position_PC = position_PC-order_size_PC
                        # buy if negative position
                        if position_PC<0:
                            order_size_PC = min(-best_ask_volume_PC, 0-position_PC)
                            print("BUY", 'PINA_COLADAS', str(order_size_PC) + "x", best_ask_PC)
                            orders_PC.append(Order('PINA_COLADAS', best_ask_PC, order_size_PC))
                            position_PC = position_PC+order_size_PC
                        # sell if posititive position
                        if position_C>0:
                            order_size_C = min(best_bid_volume_C, 0+position_C)
                            print("SELL", 'COCONUTS', str(order_size_C) + "x", best_bid_C)
                            orders_C.append(Order('COCONUTS', best_bid_C, -order_size_C))
                            position_C = position_C-order_size_C

                        # buy if negative position
                        if position_C<0:
                            order_size_C = min(-best_ask_volume_C, 0-position_C)
                            print("BUY", 'COCONUTS', str(order_size_C) + "x", best_ask_C)
                            orders_C.append(Order('COCONUTS', best_ask_C, order_size_C))
                            position_C = position_C+order_size_C
                        self.last_trade_time =0

                        self.last_trade_volume = (position_PC,position_C)
                        print('end loss liquidation')

                exit_time = 1000

                if last_trade_time>exit_time:
                    # sell if positive position
                    if position_PC>0:
                        order_size_PC = min(best_bid_volume_PC, 0+position_PC)
                        print("SELL", 'PINA_COLADAS', str(order_size_PC) + "x", best_bid_PC)
                        orders_PC.append(Order('PINA_COLADAS', best_bid_PC, -order_size_PC))
                    # buy if negative position
                    if position_PC<0:
                        order_size_PC = min(-best_ask_volume_PC, 0-position_PC)
                        print("BUY", 'PINA_COLADAS', str(order_size_PC) + "x", best_ask_PC)
                        orders_PC.append(Order('PINA_COLADAS', best_ask_PC, order_size_PC))
                    # sell if posititive position
                    if position_C>0:
                        order_size_C = min(best_bid_volume_C, 0+position_C)
                        print("SELL", 'COCONUTS', str(order_size_C) + "x", best_bid_C)
                        orders_C.append(Order('COCONUTS', best_bid_C, -order_size_C))

                    # buy if negative position
                    if position_C<0:
                        order_size_C = min(-best_ask_volume_C, 0-position_C)
                        print("BUY", 'COCONUTS', str(order_size_C) + "x", best_ask_C)
                        orders_C.append(Order('COCONUTS', best_ask_C, order_size_C))

                    self.last_trade_time =0




                # calculate whether to make a hedge or to go directional
                if len(assets[product].ask_prices)>=3 and out_position:
                    return_PC = ((best_bid_PC+best_ask_PC)/(assets['PINA_COLADAS'].ask_prices[-2]+assets['PINA_COLADAS'].ask_prices[-2])) -1
                    return_C = ((best_bid_C+best_ask_C)/(assets['COCONUTS'].ask_prices[-2]+assets['COCONUTS'].ask_prices[-2])) -1

                    return_delta = return_PC - 0.8*return_C

                    threshold = 0.0003

                    if return_delta > threshold:
                        order_size_PC = min(best_bid_volume_PC, limit_PC+position_PC)
                        order_size_C = min(-best_ask_volume_C, limit_C-position_C)

                        if order_size_PC*mid_PC < 0.8*order_size_C*mid_C:
                            order_size_C = int(np.floor(order_size_PC*mid_PC/(mid_C*0.8)))

                        if order_size_PC*mid_PC > 0.8*order_size_C*mid_C:
                            order_size_PC = int(np.floor(0.8*order_size_C*mid_C/(mid_PC)))


                        print("SELL", 'PINA_COLADAS', str(order_size_PC) + "x", best_bid_PC)
                        orders_PC.append(Order('PINA_COLADAS', best_bid_PC, -order_size_PC))


                        print("BUY", 'COCONUTS', str(order_size_C) + "x", best_ask_C)
                        orders_C.append(Order('COCONUTS', best_ask_C, order_size_C))

                        self.last_trade_time +=1
                        self.last_trade = (best_bid_PC,best_ask_C)
                        self.last_trade_volume = (-order_size_PC,order_size_C)

                    if return_delta < -threshold:
                        order_size_PC = min(-best_ask_volume_PC, limit_PC-position_PC)
                        order_size_C = min(best_bid_volume_C, limit_C+position_C)

                        if order_size_PC*mid_PC < 0.8*order_size_C*mid_C:
                            order_size_C = int(np.floor(order_size_PC*mid_PC/(mid_C*0.8)))

                        if order_size_PC*mid_PC > 0.8*order_size_C*mid_C:
                            order_size_PC = int(np.floor(0.8*order_size_C*mid_C/(mid_PC)))

                        print("BUY", 'PINA_COLADAS', str(order_size_PC) + "x", best_ask_PC)
                        orders_PC.append(Order('PINA_COLADAS', best_ask_PC, order_size_PC))


                        print("SELL", 'COCONUTS', str(order_size_C) + "x", best_bid_C)
                        orders_C.append(Order('COCONUTS', best_bid_C, -order_size_C))

                        self.last_trade_time +=1
                        self.last_trade = (best_ask_PC,best_bid_C)
                        self.last_trade_volume = (order_size_PC,-order_size_C)




                result['PINA_COLADAS'] = orders_PC
                result['COCONUTS'] = orders_C

        # Return the dict of orders
        return result
