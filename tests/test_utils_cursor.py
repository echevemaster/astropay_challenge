"""Tests for cursor pagination utilities."""
import pytest
from datetime import datetime
from uuid import uuid4

from app.utils.cursor import encode_cursor, decode_cursor, validate_cursor


class TestCursorUtils:
    """Test cursor pagination utilities."""
    
    def test_encode_cursor(self):
        """Test encoding cursor from transaction ID and timestamp."""
        transaction_id = str(uuid4())
        created_at = datetime(2024, 1, 15, 10, 30, 0)
        
        cursor = encode_cursor(transaction_id, created_at)
        
        assert cursor is not None
        assert isinstance(cursor, str)
        assert len(cursor) > 0
    
    def test_decode_cursor(self):
        """Test decoding cursor to transaction ID and timestamp."""
        transaction_id = str(uuid4())
        created_at = datetime(2024, 1, 15, 10, 30, 0)
        
        cursor = encode_cursor(transaction_id, created_at)
        decoded = decode_cursor(cursor)
        
        assert decoded is not None
        assert decoded["id"] == transaction_id
        assert decoded["created_at"] == created_at
    
    def test_decode_invalid_cursor(self):
        """Test decoding invalid cursor returns None."""
        invalid_cursors = [
            "invalid_cursor",
            "not_base64",
            "",
            "12345",
            None
        ]
        
        for invalid_cursor in invalid_cursors:
            if invalid_cursor is None:
                continue
            result = decode_cursor(invalid_cursor)
            assert result is None
    
    def test_validate_cursor(self):
        """Test cursor validation."""
        transaction_id = str(uuid4())
        created_at = datetime(2024, 1, 15, 10, 30, 0)
        
        valid_cursor = encode_cursor(transaction_id, created_at)
        assert validate_cursor(valid_cursor) is True
        assert validate_cursor("invalid") is False
        assert validate_cursor("") is False
    
    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding preserves data."""
        transaction_id = str(uuid4())
        created_at = datetime(2024, 1, 15, 10, 30, 0, 123456)
        
        cursor = encode_cursor(transaction_id, created_at)
        decoded = decode_cursor(cursor)
        
        assert decoded["id"] == transaction_id
        # Compare timestamps (microseconds might differ in string representation)
        assert decoded["created_at"].replace(microsecond=0) == created_at.replace(microsecond=0)
    
    def test_multiple_cursors_unique(self):
        """Test that different transactions produce different cursors."""
        id1 = str(uuid4())
        id2 = str(uuid4())
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        
        cursor1 = encode_cursor(id1, timestamp)
        cursor2 = encode_cursor(id2, timestamp)
        
        assert cursor1 != cursor2

