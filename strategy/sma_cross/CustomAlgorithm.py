from clr import AddReference

AddReference("System")
AddReference("System.Core")
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Algorithm.Framework")
AddReference("QuantConnect.Indicators")

from System import *
from QuantConnect import *

from QuantConnect.Data.Consolidators import *
from QuantConnect.Securities import *
from QuantConnect.Brokerages import *
from QuantConnect.Indicators import *
from QuantConnect.Orders import *
# from QuantConnect.Algorithm import *
from QuantConnect.Algorithm import *
# from QuantConnect.Algorithm.Framework.Alphas import *
# from QuantConnect.Algorithm.Framework.Portfolio import *
# from QuantConnect.Algorithm.Framework.Selection import *
# # from QuantConnect.Algorithm.Framework.Alphas.ConstantAlphaModel import ConstantAlphaModel
# from QuantConnect.Algorithm.Framework.Execution import *
# # from QuantConnect.Algorithm.Framework.Execution.ImmediateExecutionModel import ImmediateExecutionModel
# from QuantConnect.Algorithm.Framework.Risk import *
# # from QuantConnect.Algorithm.Framework.Risk.MaximumDrawdownPercentPerSecurity import MaximumDrawdownPercentPerSecurity

import os
import numpy as np
# from Deciam import decimal as d
from datetime import datetime, timedelta
import decimal as d

from custom_ohlc import CustomOHLC


class CustomFeeModel:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def GetOrderFee(self, security, order):
        # custom fee math
        fee = security.Price * order.AbsoluteQuantity * d.Decimal(0.007)
        # self.algorithm.Log("CustomFeeModel: " + str(fee))
        return fee


import json


class BasicTemplateAlgorithm(QCAlgorithm):
    '''Basic template algorithm simply initializes the date range and cash'''
    def Initialize(self):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.'''

        with open(os.environ["_STRATEGY_CONFIG"]) as f:
            strategy_config = json.load(f)

        symbol = strategy_config["asset_config"]["base"] + strategy_config["asset_config"]["quote"]
        self._symbol = symbol
        self.SetBenchmark(symbol)

        self.SetStartDate(
            *tuple(map(int, strategy_config["asset_config"]["date_range"][0].split("-")))
        )  # Set Start Date
        self.SetEndDate(
            *tuple(map(int, strategy_config["asset_config"]["date_range"][1].split("-")))
        )  # Set End Date

        self.SetCash(10000)  # Set Strategy Cash

        res = Resolution.Hour

        self.SetBrokerageModel(BrokerageName.GDAX, AccountType.Cash)

        self.security = self.AddSecurity(
            SecurityType.Crypto, symbol, res, Market.GDAX, False, 1, True
        )
        self.security.SetFeeModel(CustomFeeModel(self))

        ### The default buying power model for the Crypto security type is now CashBuyingPowerModel.
        ### Since this test algorithm uses leverage we need to set a buying power model with margin.
        self.security.BuyingPowerModel = SecurityMarginModel(1)

        self.symbol = self.security.Symbol

        if int(strategy_config["strategy_config"]['slow_length']) <= int(strategy_config["strategy_config"]['fast_length']):
            raise Exception("Slow MA can't be less the Fast MA")

        self.ma_slow_len = int(strategy_config["strategy_config"]['slow_length'])
        self.ma_fast_len = int(strategy_config["strategy_config"]['fast_length'])

        self.ma_slow = RollingWindow[float](self.ma_slow_len)
        self.ma_fast = RollingWindow[float](self.ma_fast_len)

        self.is_long_position = None


        dataConsolidator = TradeBarConsolidator(timedelta(minutes=int(strategy_config["strategy_config"]['timeframe'])))
        dataConsolidator.DataConsolidated += self.dataConsolidatorHandler
        self.SubscriptionManager.AddConsolidator(symbol, dataConsolidator)

        sym = strategy_config["asset_config"]["base"] + "_" + strategy_config["asset_config"]["quote"]
        self.AddData(CustomOHLC, sym, res)

    def dataConsolidatorHandler(self, sender, bar):
        '''This is our event handler for our 30-minute trade bar defined above in Initialize(). So each time the consolidator produces a new 30-minute bar, this function will be called automatically. The sender parameter will be the instance of the IDataConsolidator that invoked the event '''
        self.Debug(str(self.Time) + " " + str(bar))
        self.ma_fast.Add(float(bar.Close))
        self.ma_slow.Add(float(bar.Close))

        if self.ma_fast.Count < self.ma_fast_len or self.ma_slow.Count < self.ma_slow_len:
            return

        fast = sum(self.ma_fast) / self.ma_fast.Count
        slow = sum(self.ma_slow) / self.ma_slow.Count

        if fast > slow:
            if self.is_long_position == True:
                # nothing changed, holding
                return

            self.is_long_position = True

        elif fast < slow:
            if self.is_long_position == False:
                # nothing changed, holding
                return
            self.is_long_position = False

        self.Liquidate()

        if self.is_long_position:
            # self.Order("BTCUSD", 1)
            self.SetHoldings(self._symbol, 1)
        else:
            # self.Order("BTCUSD", -1)
            self.SetHoldings(self._symbol, -1)

    def OnData(self, data):
        pass
