"""Strategy pattern for processing different transaction types."""
from abc import ABC, abstractmethod
from typing import Dict, Any
from app.schemas import TransactionCreate


class TransactionStrategy(ABC):
    """Abstract base class for transaction processing strategies."""
    
    @abstractmethod
    def build_search_content(self, transaction: TransactionCreate) -> str:
        """Build searchable content from transaction data."""
        pass
    
    @abstractmethod
    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate transaction-specific metadata."""
        pass
    
    @abstractmethod
    def enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich metadata with computed fields."""
        pass


class CardPaymentStrategy(TransactionStrategy):
    """Strategy for card payment transactions."""
    
    def build_search_content(self, transaction: TransactionCreate) -> str:
        """Build searchable content for card payments."""
        parts = [
            f"Card payment {transaction.amount} {transaction.currency}",
            transaction.status.value,
        ]
        if transaction.metadata:
            if "merchant_name" in transaction.metadata:
                parts.append(transaction.metadata["merchant_name"])
            if "merchant_category" in transaction.metadata:
                parts.append(transaction.metadata["merchant_category"])
            if "location" in transaction.metadata:
                parts.append(transaction.metadata["location"])
        return " ".join(parts)
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate card payment metadata."""
        # Optional validation - can be extended
        return True
    
    def enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich card payment metadata."""
        enriched = metadata.copy() if metadata else {}
        # Add any computed fields
        return enriched


class P2PTransferStrategy(TransactionStrategy):
    """Strategy for P2P transfer transactions."""
    
    def build_search_content(self, transaction: TransactionCreate) -> str:
        """Build searchable content for P2P transfers."""
        parts = [
            f"P2P transfer {transaction.amount} {transaction.currency}",
            transaction.status.value,
        ]
        if transaction.metadata:
            if "peer_name" in transaction.metadata:
                parts.append(transaction.metadata["peer_name"])
            if "peer_email" in transaction.metadata:
                parts.append(transaction.metadata["peer_email"])
            if "direction" in transaction.metadata:
                parts.append(transaction.metadata["direction"])
        return " ".join(parts)
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate P2P transfer metadata."""
        return True
    
    def enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich P2P transfer metadata."""
        enriched = metadata.copy() if metadata else {}
        return enriched


class CryptoTransactionStrategy(TransactionStrategy):
    """Strategy for cryptocurrency transactions."""
    
    def build_search_content(self, transaction: TransactionCreate) -> str:
        """Build searchable content for crypto transactions."""
        parts = [
            f"Crypto {transaction.amount} {transaction.currency}",
            transaction.status.value,
        ]
        if transaction.metadata:
            if "crypto_type" in transaction.metadata:
                parts.append(transaction.metadata["crypto_type"])
            if "wallet_address" in transaction.metadata:
                parts.append(transaction.metadata["wallet_address"])
        return " ".join(parts)
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate crypto transaction metadata."""
        return True
    
    def enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich crypto transaction metadata."""
        enriched = metadata.copy() if metadata else {}
        return enriched


class TransactionStrategyFactory:
    """Factory for creating transaction strategies."""
    
    _strategies = {
        "card": CardPaymentStrategy(),
        "p2p": P2PTransferStrategy(),
        "crypto": CryptoTransactionStrategy(),
    }
    
    @classmethod
    def get_strategy(cls, transaction_type: str) -> TransactionStrategy:
        """Get strategy for transaction type."""
        strategy = cls._strategies.get(transaction_type)
        if not strategy:
            # Default strategy for unknown types
            return DefaultTransactionStrategy()
        return strategy


class DefaultTransactionStrategy(TransactionStrategy):
    """Default strategy for unknown transaction types."""
    
    def build_search_content(self, transaction: TransactionCreate) -> str:
        """Build default searchable content."""
        return f"{transaction.transaction_type.value} {transaction.amount} {transaction.currency} {transaction.status.value}"
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Default validation."""
        return True
    
    def enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Default enrichment."""
        return metadata.copy() if metadata else {}

