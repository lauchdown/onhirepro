"""
OnHire Pro - Rental Management Application for ERPNext

This module provides error handling utilities for the OnHire Pro application.
These functions are used to standardize error handling and logging across
all modules of the application.

The module implements a consistent approach to error handling, including:
- Standardized error classes
- Consistent error logging
- User-friendly error messages
- Detailed error tracking for debugging
"""

import frappe
import logging
import traceback
import json
from typing import Dict, List, Optional, Union, Any, Callable

# Configure logger
logger = logging.getLogger(__name__)

class OnHireProError(Exception):
    """Base exception class for all OnHire Pro errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class SchemaError(OnHireProError):
    """Exception raised for schema-related errors."""
    pass

class KPICalculationError(OnHireProError):
    """Exception raised for KPI calculation errors."""
    pass

class ConfigurationError(OnHireProError):
    """Exception raised for configuration errors."""
    pass

class DataError(OnHireProError):
    """Exception raised for data-related errors."""
    pass

def log_error(error: Exception, error_type: str, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an error with standardized format and context.
    
    Args:
        error (Exception): The exception to log
        error_type (str): Type of error (e.g., 'KPI Calculation', 'Schema Verification')
        context (dict, optional): Additional context information
        
    Example:
        >>> try:
        ...     result = calculate_item_utilization_rate(filters)
        ... except Exception as e:
        ...     log_error(e, 'KPI Calculation', {'filters': filters})
    """
    context = context or {}
    
    error_details = {
        "error_type": error_type,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context
    }
    
    # Log to frappe error log
    frappe.log_error(
        message=f"{error_type} Error: {str(error)}",
        title=f"OnHire Pro {error_type} Error",
        reference_doctype=context.get("doctype"),
        reference_name=context.get("docname")
    )
    
    # Also log to Python logger for server logs
    logger.error(
        f"{error_type} Error: {str(error)}",
        extra={"error_details": json.dumps(error_details, default=str)}
    )

def safe_execute(func: Callable, error_type: str, default_return: Any = None, 
                 context: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    Execute a function with standardized error handling.
    
    Args:
        func (callable): Function to execute
        error_type (str): Type of error for logging
        default_return (any, optional): Default value to return on error
        context (dict, optional): Additional context information
        **kwargs: Arguments to pass to the function
        
    Returns:
        any: Result of the function or default_return on error
        
    Example:
        >>> result = safe_execute(
        ...     calculate_item_utilization_rate, 
        ...     'KPI Calculation',
        ...     {"value": 0},
        ...     {"doctype": "Rental Job"},
        ...     filters={"company": "Example Inc."}
        ... )
    """
    try:
        return func(**kwargs)
    except Exception as e:
        log_error(e, error_type, context)
        return default_return

def validate_required_filters(filters: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    Validate that required filters are present.
    
    Args:
        filters (dict): Dictionary of filters
        required_fields (list): List of required field names
        
    Returns:
        bool: True if all required filters are present, False otherwise
        
    Example:
        >>> validate_required_filters({"company": "Example Inc."}, ["company", "from_date"])
        False
    """
    if not filters:
        return False
        
    for field in required_fields:
        if field not in filters or not filters[field]:
            return False
            
    return True

def format_error_response(error_message: str) -> Dict[str, Any]:
    """
    Format a standardized error response for API endpoints.
    
    Args:
        error_message (str): Error message
        
    Returns:
        dict: Standardized error response
        
    Example:
        >>> format_error_response("Missing required filters")
        {'success': False, 'error': 'Missing required filters'}
    """
    return {
        "success": False,
        "error": error_message
    }

def handle_api_exception(e: Exception) -> Dict[str, Any]:
    """
    Handle exceptions in API endpoints with standardized response.
    
    Args:
        e (Exception): The exception to handle
        
    Returns:
        dict: Standardized error response
        
    Example:
        >>> try:
        ...     result = calculate_kpi(filters)
        ...     return {"success": True, "data": result}
        ... except Exception as e:
        ...     return handle_api_exception(e)
    """
    if isinstance(e, OnHireProError):
        # Custom application error
        return {
            "success": False,
            "error": e.message,
            "details": e.details
        }
    elif isinstance(e, frappe.ValidationError):
        # Frappe validation error
        return {
            "success": False,
            "error": str(e),
            "validation_error": True
        }
    elif isinstance(e, frappe.DoesNotExistError):
        # Document not found error
        return {
            "success": False,
            "error": str(e),
            "not_found": True
        }
    elif isinstance(e, frappe.PermissionError):
        # Permission error
        return {
            "success": False,
            "error": "You do not have permission to perform this action",
            "permission_error": True
        }
    else:
        # Generic error
        log_error(e, "API", {})
        return {
            "success": False,
            "error": "An unexpected error occurred",
            "reference": frappe.generate_hash(length=8)  # For error tracking
        }
