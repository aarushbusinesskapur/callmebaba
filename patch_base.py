import re

with open('skills/base.py', 'r') as f:
    content = f.read()

# Add gross_profit and gross_loss to BacktestResult
content = content.replace("total_trades: int", "total_trades: int\n    gross_profit: float = 0.0\n    gross_loss: float = 0.0")

# In base backtester (if it has default backtester? No, base.py is abstract).
# Let's see if we need to modify every skill to return gross_profit and gross_loss.
