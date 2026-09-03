def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamps a value between a minimum and maximum."""
    return max(min_val, min(value, max_val))

def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b."""
    return a + (b - a) * clamp(t, 0.0, 1.0)
