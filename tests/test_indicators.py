import pandas as pd
import numpy as np
from src.strategies.indicators import Indicators

def test_sma():
    data = pd.Series([10, 20, 30, 40, 50])
    sma = Indicators.sma(data, 3)
    assert np.isnan(sma[0])
    assert np.isnan(sma[1])
    assert sma[2] == 20.0
    assert sma[4] == 40.0

def test_ema():
    data = pd.Series([10, 10, 10, 10])
    ema = Indicators.ema(data, 3)
    assert ema[3] == 10.0
