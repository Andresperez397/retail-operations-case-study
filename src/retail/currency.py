"""Currency: the source data is in British pounds (GBP); every figure in this project is reported in US dollars.

One fixed rate converts all amounts, so every share, ranking and decision is identical to the GBP analysis;
only the dollar amounts are rescaled. The rate is the mean of the Federal Reserve's daily noon buying rate
(FRED series DEXUSUK, US dollars per pound) over the data period, 2009-12-01 to 2011-12-09: 509 business
days, mean 1.5774 (range 1.4344 to 1.6691).
"""

USD_PER_GBP = 1.5774
