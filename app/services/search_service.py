"""Search service using Elasticsearch."""
from typing import List, Optional, Dict, Any
from elasticsearch import Elasticsearch
from app.config import settings
from app.middleware.circuit_breaker import get_elasticsearch_breaker, CircuitBreakerOpenError
import structlog

logger = structlog.get_logger()


class SearchService:
    """Service for full-text search operations."""
    
    def __init__(self):
        try:
            self.es_client = Elasticsearch(
                [settings.elasticsearch_url],
                request_timeout=5,
                max_retries=3,
                retry_on_timeout=True,
            )
            # Test connection
            self.es_client.ping()
            self.enabled = True
            self._ensure_index_exists()
        except Exception as e:
            logger.warning("Elasticsearch connection failed, search disabled", error=str(e))
            self.es_client = None
            self.enabled = False
    
    def _ensure_index_exists(self):
        """Ensure Elasticsearch index exists with proper mapping."""
        if not self.enabled:
            return
        
        index_name = "transactions"
        if not self.es_client.indices.exists(index=index_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "transaction_type": {"type": "keyword"},
                        "product": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "currency": {"type": "keyword"},
                        "amount": {"type": "float"},
                        "created_at": {"type": "date"},
                        "search_content": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "metadata": {"type": "object", "enabled": True}
                    }
                }
            }
            self.es_client.indices.create(index=index_name, body=mapping)
            logger.info("Created Elasticsearch index", index=index_name)
    
    def index_transaction(self, transaction: Dict[str, Any], version: Optional[int] = None) -> bool:
        """Index a transaction in Elasticsearch.
        
        Args:
            transaction: Transaction document to index
            version: Optional version number (for optimistic concurrency control)
        """
        if not self.enabled:
            return False
        try:
            breaker = get_elasticsearch_breaker()
            
            # Remove metadata fields from document before indexing
            doc = transaction.copy()
            doc.pop("_version", None)  # Remove _version from document
            doc.pop("_updated_at", None)  # Keep _updated_at as regular field if needed
            
            # Prepare index parameters
            index_params = {
                "index": "transactions",
                "id": str(transaction["id"]),
                "document": doc
            }
            
            # Add version as API parameter if provided
            if version is not None:
                index_params["version"] = version
                index_params["version_type"] = "external_gte"  # external_gte allows updates if new version >= existing
            
            breaker.call(
                self.es_client.index,
                **index_params
            )
            return True
        except CircuitBreakerOpenError:
            logger.warning("Elasticsearch index skipped: circuit breaker open")
            return False
        except Exception as e:
            logger.warning("Failed to index transaction", error=str(e))
            return False
    
    def search(
        self,
        user_id: str,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        return_documents: bool = False
    ) -> tuple:
        """
        Search transactions for a user using Elasticsearch.
        
        Args:
            user_id: User ID to filter by
            query: Optional search query (if None, returns all matching filters)
            filters: Optional filters (transaction_type, product, status, currency, metadata)
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number
            page_size: Page size
            return_documents: If True, returns full documents instead of just IDs
        
        Returns:
            Tuple of (transaction_ids or documents, total_count)
        """
        if not self.enabled:
            logger.warning("Elasticsearch search called but service is disabled")
            return ([], 0) if not return_documents else ([], 0)
        
        try:
            # Build base query with user_id filter
            must_clauses = [{"term": {"user_id": user_id}}]
            
            # Add text search if query is provided
            if query:
                must_clauses.append({
                    "match": {
                        "search_content": {
                            "query": query,
                            "fuzziness": "AUTO",
                            "operator": "or"
                        }
                    }
                })
            
            es_query = {
                "bool": {
                    "must": must_clauses
                }
            }
            
            # Add filters
            filter_clauses = []
            
            # Add standard filters
            if filters:
                if filters.get("transaction_type"):
                    filter_clauses.append({"term": {"transaction_type": filters["transaction_type"]}})
                if filters.get("product"):
                    filter_clauses.append({"term": {"product": filters["product"]}})
                if filters.get("status"):
                    filter_clauses.append({"term": {"status": filters["status"]}})
                if filters.get("currency"):
                    filter_clauses.append({"term": {"currency": filters["currency"]}})
                
                # Add metadata filters (e.g., card_last_four, direction, etc.)
                metadata_filters = filters.get("metadata_filters", {})
                if metadata_filters:
                    for key, value in metadata_filters.items():
                        # Use nested query for metadata fields
                        filter_clauses.append({
                            "term": {f"metadata.{key}": str(value)}
                        })
                
                # Add amount filters
                if filters.get("min_amount") is not None:
                    filter_clauses.append({
                        "range": {
                            "amount": {
                                "gte": filters["min_amount"]
                            }
                        }
                    })
                if filters.get("max_amount") is not None:
                    filter_clauses.append({
                        "range": {
                            "amount": {
                                "lte": filters["max_amount"]
                            }
                        }
                    })
            
            # Add date range filters
            if start_date or end_date:
                date_range = {}
                if start_date:
                    date_range["gte"] = start_date
                if end_date:
                    date_range["lte"] = end_date
                filter_clauses.append({"range": {"created_at": date_range}})
            
            if filter_clauses:
                es_query["bool"]["filter"] = filter_clauses
            
            search_body = {
                "query": es_query,
                "sort": [{"created_at": {"order": "desc"}}],
                "from": (page - 1) * page_size,
                "size": page_size
            }
            
            logger.debug("Executing Elasticsearch query", query=query, user_id=user_id, return_documents=return_documents)
            breaker = get_elasticsearch_breaker()
            response = breaker.call(self.es_client.search, index="transactions", body=search_body)
            
            total = response["hits"]["total"]["value"]
            
            if return_documents:
                # Return full documents
                documents = []
                for hit in response["hits"]["hits"]:
                    doc = hit["_source"]
                    doc["id"] = hit["_id"]  # Ensure ID is in the document
                    documents.append(doc)
                
                logger.info(
                    "Elasticsearch search successful (returning documents)",
                    user_id=user_id,
                    query=query,
                    results_count=len(documents),
                    total=total
                )
                
                return documents, total
            else:
                # Return only IDs (backward compatibility)
                transaction_ids = [hit["_id"] for hit in response["hits"]["hits"]]
                
                logger.info(
                    "Elasticsearch search successful",
                    user_id=user_id,
                    query=query,
                    results_count=len(transaction_ids),
                    total=total
                )
                
                return transaction_ids, total
        except CircuitBreakerOpenError:
            logger.warning("Elasticsearch search skipped: circuit breaker open", query=query, user_id=user_id)
            return [], 0
        except Exception as e:
            logger.error("Elasticsearch search failed", error=str(e), query=query, user_id=user_id)
            return [], 0
    
    def delete_transaction(self, transaction_id: str) -> bool:
        """Delete a transaction from the search index."""
        if not self.enabled:
            return False
        try:
            self.es_client.delete(index="transactions", id=transaction_id)
            return True
        except Exception as e:
            logger.warning("Failed to delete from search index", error=str(e))
            return False
    
    def health_check(self) -> bool:
        """Check if search service is healthy."""
        if not self.enabled:
            return False
        try:
            return self.es_client.ping()
        except Exception:
            return False

