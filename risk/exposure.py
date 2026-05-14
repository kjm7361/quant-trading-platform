def cap_exposure(positions, max_gross=1.5):
    gross = positions.abs().sum(axis=1)
    scale = max_gross / gross
    scale[scale > 1] = 1
    return positions.mul(scale, axis=0)
