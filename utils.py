def normalize(value, min_val, max_val):
    if value < min_val: return 0
    if value > max_val: return 100
    return ((value - min_val) / (max_val - min_val)) * 100

def get_rating(score):
    if score >= 80: return "Strong Bullish", "#f2ca50"
    if score >= 60: return "Bullish Bias", "#d4af37"
    if score >= 40: return "Neutral / Mixed", "#a89060"
    if score >= 20: return "Bearish Bias", "#ff8070"
    return "Strong Bearish", "#ff4444"