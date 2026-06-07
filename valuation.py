def compute_valuation(current_eps, g, pe, n, r, mos):
    """
    current_eps : trailing EPS
    g : annual growth rate
    pe : exit P/E multiple
    n : projection years
    r : discount rate (decimal)
    mos : margin of safety (decimal, e.g. 0.50)
    """
    future_eps    = current_eps * (1 + g) ** n
    future_price  = future_eps * pe
    intrinsic_val = future_price / (1 + r) ** n
    fair_value    = intrinsic_val * (1 - mos)
    return {
        "future_eps":    future_eps,
        "future_price":  future_price,
        "intrinsic_val": intrinsic_val,
        "fair_value":    fair_value,
    }
 