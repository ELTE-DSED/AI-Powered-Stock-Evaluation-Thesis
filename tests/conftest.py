import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def mock_stock_data():
    """Creates 100 days of fake stock price data for technical analysis testing."""
    dates = pd.date_range(start="2023-01-01", periods=100)
    data = {
        'Open': np.linspace(100, 150, 100),
        'High': np.linspace(105, 155, 100),
        'Low': np.linspace(95, 145, 100),
        'Close': np.linspace(102, 152, 100),
        'Volume': np.random.randint(1000, 5000, 100)
    }
    return pd.DataFrame(data, index=dates)

@pytest.fixture
def mock_financials():
    """Creates a mock Series for fundamental scoring."""
    return pd.Series([100, 80, 60], index=[0, 1, 2]) # Current, Previous, Year-Before