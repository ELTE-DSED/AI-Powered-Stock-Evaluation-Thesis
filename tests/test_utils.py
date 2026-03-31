from utils import get_rating, normalize

def test_get_rating_bounds():
    # Test Strong Bullish 
    label, color = get_rating(85)
    assert label == "Strong Bullish"
    assert color == "#f2ca50"
    
    # Test Strong Bearish 
    label, color = get_rating(10)
    assert label == "Strong Bearish"
    assert color == "#ff4444"

def test_normalize_function():
    # Test standard normalization 
    assert normalize(5, 0, 10) == 50.0
    # Test capping at 100 
    assert normalize(15, 0, 10) == 100
    # Test bottoming at 0 
    assert normalize(-5, 0, 10) == 0