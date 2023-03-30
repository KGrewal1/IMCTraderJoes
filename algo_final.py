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
                "BERRIES":Asset(250, 10, 10),
                "DIVING_GEAR":Asset(50, 10, 10),
                "DIP": Asset(300, 100, 10),
                "BAGUETTE": Asset(150, 100, 10),
                "UKULELE": Asset(70, 100, 10),
                "PICNIC_BASKET": Asset(70, 100, 10)
            }
        self.asset_dicts = assets
        self.printing = printing
        self.position = {"PEARLS": 0, "BANANAS": 0,
                        "COCONUTS": 0, "PINA_COLADAS": 0,
                        "BERRIES": 0, "DIVING_GEAR": 0,
                        "DIP": 0, "BAGUETTE": 0, "UKULELE": 0, "PICNIC_BASKET": 0}
        #berries
        self.berries_highs = set()
        self.berries_active = False

        #coco-pina
        self.short = False
        self.long = False
        self.resMA = 0
        self.zscore = None
        self.zscore_low = 0.5 #edit
        self.zscore_high = 2.0

        #dolphin diving gear
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
        # Initialize the method output dict as an empty dict
        result = {}
        # Iterate over all the keys (the available products) contained in the order depths
        for product in state.order_depths.keys():
            if product != 'DOLPHIN_SIGHTINGS':
                self.position[product] = state.position.get(product, 0)
            ''' STRAT 1 PEARLS: MM and spike misspricing  '''
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
                ##########################################################
                order_depth: OrderDepth = state.order_depths[product]
                threshold = 6
                spread = min(list(order_depth.sell_orders.keys()))-max(list(order_depth.buy_orders.keys()))
                if spread >= threshold:
                    #adjust volumes later
                    #bid
                    bid_size = np.floor(10*(1-position/20))
                    if position != assets[product].limit and bid_size == 0:
                        if spread >= threshold+2:
                            bid_size = 1
                    bid = max(order_depth.buy_orders.keys())+1
                    orders.append(Order(product, bid, bid_size))
                    #ask
                    ask_size = -np.floor(10*(1+position/20))
                    if position != assets[product].limit and ask_size == 0:
                        if spread >= threshold+2:
                            ask_size = 1
                    ask = min(order_depth.sell_orders.keys())-1
                    orders.append(Order(product, ask, ask_size))
                    print('Spread:', spread, "MM BUY", product, str(bid_size) + "x", bid, 'position:', position, "MM SELL", product, str(-ask_size) + "x", ask,  'position:', position)
                ##########################################################

                # Add all the above orders to the result dict
                result[product] = orders

            ''' STRAT 2 BANANAS: MM and spike misspricing  '''
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

                ##########################################################
                if spread >= threshold:
                    #adjust volumes later
                    #bid
                    order_size = np.floor(5*(1-position/20)) #limtransform(position, 20, abs(best_bid_volume), abs(best_ask_volume)) #
                    print('bid size',order_size)
                    print('bid vol',best_bid_volume)
                    print('ask vol',best_ask_volume)
                    bid = max(order_depth.buy_orders.keys())+1
                    orders.append(Order(product, bid, order_size))
                    print(spread)
                    print("MM BUY", product, str(order_size) + "x", bid, 'position:', position)
                    #ask
                    order_size = -np.floor(5*(1+position/20)) #-limtransform(-position, 20, abs(best_ask_volume), abs(best_bid_volume))  #
                    ask = min(order_depth.sell_orders.keys())-1
                    orders.append(Order(product, ask, order_size))
                    print("MM SELL", product, str(-order_size) + "x", ask,  'position:', position)
                ##########################################################

                # Add all the above orders to the result dict
                result[product] = orders

            ''' STRAT 4 BERRIES: LONG from MM BUYS then max SHORT from midday peak  '''
            if product == 'BERRIES':

                # Retrieve the Order Depth containing all the market BUY and SELL orders for BERRIES
                order_depth: OrderDepth = state.order_depths[product]

                try:
                    position = state.position[product]
                except KeyError:
                    position = 0
                # Initialize the list of Orders to be sent as an empty list
                orders: list[Order] = []

                # If statement checks if there are any SELL orders in the BERRIES market
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
                start = 480000    # with leway from min original 480000
                duration = 40000  # original 40000
                if (start < state.timestamp < start+duration): #if spread < threshold:
                    if len(assets[product].ask_prices)>=assets[product].period:
                        fast_avg = (sum(assets[product].ask_prices[-assets[product].fast_period:])+sum(assets[product].bid_prices[-assets[product].fast_period:]))/(2*assets[product].fast_period)
                        #check for sell signal at midday highest price
                        if (fast_avg - 1) < best_bid:

                            self.berries_active = True
                            order_size = min(best_bid_volume, assets[product].limit+position)
                            if order_size > 0:
                                print("SELL", product, str(order_size) + "x", best_bid)
                                orders.append(Order(product, best_bid, -order_size))
                            if len(self.berries_highs) == 0:
                                self.berries_highs.add(best_bid)
                            if (best_bid > min(self.berries_highs)):
                                self.berries_highs.add(best_bid)
                                if len(self.berries_highs) >= 5:
                                    self.berries_highs.remove(min(self.berries_highs))

                        #sell signal based off new high #elif, dont want if already above loop run
                        elif self.berries_active:
                            if (best_bid > min(self.berries_highs)):
                                order_size = min(best_bid_volume, assets[product].limit+position)
                                if order_size > 0:
                                    print("SELL", product, str(order_size) + "x", best_bid)
                                    orders.append(Order(product, best_bid, -order_size))
                                self.berries_highs.add(best_bid)
                                if len(self.berries_highs) >= 5:
                                    self.berries_highs.remove(min(self.berries_highs))

                        #check for buy signal
                        elif fast_avg > best_ask and state.timestamp < 400000:
                            #available_to_buy = True
                            order_size = min(-best_ask_volume, assets[product].limit-position)
                            if order_size > 0:
                                print("BUY", product, str(order_size) + "x", best_ask)
                                orders.append(Order(product, best_ask, order_size))

                ##########################################################
                if spread >= threshold and state.timestamp < 400000:
                    #adjust volumes later
                    #bid                 #50
                    order_size = np.floor(10*(1-position/250)) #change size 5
                    if position != 250 and order_size == 0:
                        order_size = np.floor((250-position)/2)
                        if position != 250 and order_size == 0:
                            order_size = 1
                    bid = max(order_depth.buy_orders.keys())+1
                    orders.append(Order(product, bid, order_size))
                    print(spread)
                    print("MM BUY", product, str(order_size) + "x", bid, 'position:', position)
                    #ask
                    order_size = -np.floor(10*(1+position/250)) #change size 5
                    ask = min(order_depth.sell_orders.keys())-1
                    orders.append(Order(product, ask, order_size))
                    print("MM SELL", product, str(-order_size) + "x", ask,  'position:', position)
                ##########################################################

                # Add all the above orders to the result dict
                result[product] = orders

            ''' STRAT 5 DOLPHIN_SIGHTINGS peak DIVING_GEAR'''
            if product == 'DIVING_GEAR':
                order_depth_gear = state.order_depths["DIVING_GEAR"]
                best_ask_gear, best_ask_volume_gear, best_bid_gear, best_bid_volume_gear, _, all_asks, all_bids = self.get_data(order_depth_gear)
                # Initialize the method output dict as an empty dict
                orders_gear: list[Order] = []

                self.position[product] = state.position.get(product, 0)
                observations = state.observations['DOLPHIN_SIGHTINGS']

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

        ''' STRAT 3 pairs trading COCONUTS and PINA_COLADAS '''
        # hedge ratio COCO/PINA optimum calculated 1.87
        hedge_ratio = 1.875
        orders_coconut: list[Order] = []
        orders_pina: list[Order] = []
        order_depth_coconut = state.order_depths["COCONUTS"]
        best_ask_coconut, best_ask_volume_coconut, best_bid_coconut, best_bid_volume_coconut, mid_coconut, _, _ = self.get_data(
            order_depth_coconut)
        position_coconut = state.position.get('COCONUTS', 0)
        order_depth_pina = state.order_depths["PINA_COLADAS"]
        best_ask_pina, best_ask_volume_pina, best_bid_pina, best_bid_volume_pina, mid_pina, _, _ = self.get_data(
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
            self.zscore = (res-self.resMA)/np.std(assets['COCONUTS'].residual)
            print('ready to trade')
            data_ready = True

        if data_ready:
            # entry signal SHORT res
            if self.zscore >= self.zscore_high and not self.short: # and self.zscore<self.last_zscore:
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

        ''' STRAT 6 ETF of picnic basket '''
        orders_dip: list[Order] = []
        orders_baguette: list[Order] = []
        orders_ukulele: list[Order] = []
        orders_basket: list[Order] = []

        #get data
        order_depth_dip = state.order_depths["DIP"]
        best_ask_dip, best_ask_volume_dip, best_bid_dip, best_bid_volume_dip, mid_dip, _, __ = self.get_data(
            order_depth_dip)
        order_depth_baguette = state.order_depths["BAGUETTE"]
        best_ask_baguette, best_ask_volume_baguette, best_bid_baguette, best_bid_volume_baguette, mid_baguette, _, __ = self.get_data(
            order_depth_baguette)
        order_depth_ukulele = state.order_depths["UKULELE"]
        best_ask_ukulele, best_ask_volume_ukulele, best_bid_ukulele, best_bid_volume_ukulele, mid_ukulele, _, __ = self.get_data(
            order_depth_ukulele)
        order_depth_basket = state.order_depths["PICNIC_BASKET"]
        best_ask_basket, best_ask_volume_basket, best_bid_basket, best_bid_volume_basket, mid_basket, _, __ = self.get_data(
            order_depth_basket)

        #positions
        position_baguette = state.position.get('BAGUETTE', 0)
        position_dip = state.position.get('DIP', 0)
        position_ukulele = state.position.get('UKULELE', 0)
        position_basket = state.position.get('PICNIC_BASKET', 0)

        # check all data ready
        if all([mid_dip, mid_baguette, mid_ukulele, mid_basket]) is not None:
            #redem is short basket long components
            best_ask_components = 2*best_ask_baguette + 4*best_ask_dip + best_ask_ukulele
            residual = best_bid_basket-best_ask_components

            threshold = 7
            spread = best_ask_basket-best_bid_basket
            #residual strat
            if spread < threshold:
                sell_range = 400
                buy_range = 300
                # buy signal
                if residual > sell_range:
                    # SELL basket BUY components baguette dip ukulele 2:4:1
                    #component vol is of ukuleles
                    component_volume  = min(np.floor(-best_ask_volume_baguette/2),  np.floor(-best_ask_volume_dip/4), -best_ask_volume_ukulele)
                    component_volume_lim = min(assets['BAGUETTE'].limit - position_baguette,
                                               assets['DIP'].limit - position_dip,
                                               assets['UKULELE'].limit - position_ukulele)
                    bid_volume = min(component_volume, component_volume_lim)
                    ask_volume = min(best_bid_volume_basket, assets['PICNIC_BASKET'].limit + position_basket)
                    basket_order_size = np.floor(min(bid_volume, ask_volume))
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
                # sell signal
                elif residual < buy_range:
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
            #MM strat
            elif spread > threshold:
                #MM strategy
                m=0
            # Add all the above orders to the result dict
            result["BAGUETTE"] = orders_baguette
            result["DIP"] = orders_dip
            result["UKULELE"] = orders_ukulele
            result["PICNIC_BASKET"] = orders_basket
            print(f'Position in basket: {position_basket}')
        # Return the dict of orders
        return result