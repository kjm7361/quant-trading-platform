def max_drawdown_filter(equity, max_dd=0.2):
    dd = equity / equity.cummax() - 1
    return dd > -max_dd
