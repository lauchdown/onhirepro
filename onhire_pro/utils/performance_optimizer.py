"""Enhanced Performance Optimizer"""

import frappe
import time
import logging
import json
from functools import wraps
from typing import Dict, List, Optional, Union, Any, Callable
from frappe.cache_manager import redis_cache

# Configure Redis cache
CACHE_KEY_PREFIX = "onhire_pro:"
DEFAULT_CACHE_TIMEOUT = 300  # 5 minutes

def cache_key(key: str) -> str:
    """Generate standardized cache key"""
    return f"{CACHE_KEY_PREFIX}{key}"

@redis_cache
def cached_query(query: str, params: tuple = None, expires_in: int = DEFAULT_CACHE_TIMEOUT) -> List[Dict]:
    """Execute and cache database queries"""
    return frappe.db.sql(query, params, as_dict=True)

def clear_cache_for_doctype(doctype: str) -> None:
    """Clear all cached queries for a doctype"""
    cache_key_pattern = f"{CACHE_KEY_PREFIX}{doctype}:*"
    frappe.cache().delete_keys(cache_key_pattern)

class QueryOptimizer:
    """Optimize and cache database queries"""
    
    @staticmethod
    def optimize_filters(filters: Dict) -> Dict:
        """Optimize filter conditions"""
        if not filters:
            return {}
            
        optimized = filters.copy()
        
        # Add commonly used indexes
        if "creation" in optimized:
            optimized["_index_hint"] = "creation_idx"
        elif "modified" in optimized:
            optimized["_index_hint"] = "modified_idx"
            
        return optimized
    
    @staticmethod
    def build_query(doctype: str, fields: List[str], filters: Dict,
                   order_by: str = None, limit: int = None) -> str:
        """Build optimized SQL query"""
        # Implementation remains the same but with better optimization
        pass

class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self):
        self.metrics = {}
    
    def start_operation(self, operation_name: str) -> None:
        """Start timing an operation"""
        self.metrics[operation_name] = {
            "start_time": time.time(),
            "end_time": None,
            "duration": None
        }
    
    def end_operation(self, operation_name: str) -> None:
        """End timing an operation"""
        if operation_name in self.metrics:
            self.metrics[operation_name]["end_time"] = time.time()
            self.metrics[operation_name]["duration"] = (
                self.metrics[operation_name]["end_time"] -
                self.metrics[operation_name]["start_time"]
            )
    
    def get_metrics(self) -> Dict:
        """Get all performance metrics"""
        return self.metrics

# Initialize global performance monitor
performance_monitor = PerformanceMonitor()

def monitor_performance(operation_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            performance_monitor.start_operation(operation_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                performance_monitor.end_operation(operation_name)
        return wrapper
    return decorator

@monitor_performance("database_query")
def execute_query(query: str, params: tuple = None) -> List[Dict]:
    """Execute database query with monitoring"""
    return frappe.db.sql(query, params, as_dict=True)

# Add the rest of the performance optimization code...
