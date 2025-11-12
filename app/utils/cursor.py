"""Cursor pagination utilities."""
import base64
import json
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


def encode_cursor(transaction_id: str, created_at: datetime) -> str:
    """
    Encode cursor from transaction ID and created_at timestamp.
    
    Args:
        transaction_id: UUID string of the transaction
        created_at: Datetime when transaction was created
        
    Returns:
        Base64 encoded cursor string
    """
    cursor_data = {
        "id": str(transaction_id),
        "created_at": created_at.isoformat()
    }
    json_str = json.dumps(cursor_data, sort_keys=True)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> Optional[Dict[str, Any]]:
    """
    Decode cursor to get transaction ID and created_at.
    
    Args:
        cursor: Base64 encoded cursor string
        
    Returns:
        Dictionary with 'id' and 'created_at' keys, or None if invalid
    """
    try:
        decoded_bytes = base64.urlsafe_b64decode(cursor.encode())
        cursor_data = json.loads(decoded_bytes.decode())
        return {
            "id": cursor_data["id"],
            "created_at": datetime.fromisoformat(cursor_data["created_at"])
        }
    except (ValueError, KeyError, json.JSONDecodeError, TypeError):
        return None


def validate_cursor(cursor: str) -> bool:
    """
    Validate if a cursor string is valid.
    
    Args:
        cursor: Cursor string to validate
        
    Returns:
        True if valid, False otherwise
    """
    return decode_cursor(cursor) is not None

