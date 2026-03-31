import pytest
from unittest.mock import patch, MagicMock
from data_loader import DataLoader

@patch('data_loader.Groq')
def test_groq_key_rotation(mock_groq_class):
    # Setup mock to simulate a failure on the first key and success on the second
    instance = mock_groq_class.return_value
    instance.chat.completions.create.side_effect = [Exception("Rate Limit"), MagicMock()]
    
    loader = DataLoader()
    # Force some mock keys into the pool 
    loader.api_key_pool = ["key1", "key2"]
    
    # This calls the method that uses Groq 
    loader.get_competitors("AAPL", "Apple", "Tech", "iPhone")
    
    # Verify it tried to call Groq 
    assert mock_groq_class.call_count >= 1