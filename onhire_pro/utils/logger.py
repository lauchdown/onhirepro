"""
Advanced logging system with structured logging, rotation, and monitoring
"""
import frappe
import logging
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from logging.handlers import RotatingFileHandler
import os
import sys
from functools import wraps

class LogLevel:
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory:
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    BUSINESS = "BUSINESS"
    AUDIT = "AUDIT"

class StructuredLogger:
    def __init__(self):
        self.log_levels = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL
        }
        
        self.setup_logger()
        
    def setup_logger(self) -> None:
        """Configure advanced logging setup"""
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(frappe.get_site_path(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup rotating file handler
        log_file = os.path.join(log_dir, 'onhire_pro.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(trace_id)s] %(message)s'
        )
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        
        # Set formatters
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
    def _format_log(
        self,
        level: str,
        message: str,
        category: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format log entry with enhanced context"""
        return {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "category": category,
            "message": message,
            "user": frappe.session.user,
            "site": frappe.local.site,
            "context": context,
            "trace_id": frappe.generate_hash(length=8),
            "session_id": frappe.session.sid,
            "request_id": getattr(frappe.local, 'request_id', None),
            "ip_address": frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else None
        }
    
    def _write_to_db(self, log_entry: Dict[str, Any]) -> None:
        """Write log entry to database with enhanced metadata"""
        try:
            frappe.get_doc({
                "doctype": "Error Log",
                "error": json.dumps(log_entry, indent=2),
                "method": log_entry.get("context", {}).get("method"),
                "error_type": log_entry["level"],
                "error_category": log_entry["category"],
                "trace_id": log_entry["trace_id"],
                "user": log_entry["user"],
                "creation": log_entry["timestamp"]
            }).insert(ignore_permissions=True)
        except Exception as e:
            logging.error(f"Failed to write log to database: {str(e)}")

    def log(
        self,
        level: str,
        message: str,
        category: str = LogCategory.SYSTEM,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log message with enhanced context and categorization"""
        try:
            context = context or {}
            log_entry = self._format_log(level, message, category, context)
            
            # Write to database for ERROR and CRITICAL levels
            if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                self._write_to_db(log_entry)
            
            # Write to system log
            logging.log(
                self.log_levels.get(level, logging.INFO),
                json.dumps(log_entry),
                extra={"trace_id": log_entry["trace_id"]}
            )
            
        except Exception as e:
            # Fallback logging
            logging.error(f"Logging failed: {str(e)}")

    def audit_log(
        self,
        action: str,
        doctype: str,
        doc_name: str,
        changes: Dict[str, Any],
        user: str = None
    ) -> None:
        """Log audit trail for document changes"""
        context = {
            "action": action,
            "doctype": doctype,
            "doc_name": doc_name,
            "changes": changes,
            "user": user or frappe.session.user
        }
        
        self.log(
            LogLevel.INFO,
            f"Audit: {action} on {doctype} {doc_name}",
            LogCategory.AUDIT,
            context
        )

    def security_log(
        self,
        event: str,
        details: Dict[str, Any],
        severity: str = LogLevel.INFO
    ) -> None:
        """Log security-related events"""
        self.log(
            severity,
            f"Security: {event}",
            LogCategory.SECURITY,
            details
        )

    def performance_log(
        self,
        operation: str,
        execution_time: float,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log performance metrics"""
        context = context or {}
        context.update({
            "operation": operation,
            "execution_time": execution_time
        })
        
        self.log(
            LogLevel.INFO,
            f"Performance: {operation} took {execution_time:.2f}s",
            LogCategory.PERFORMANCE,
            context
        )

def log_function_call(category: str = LogCategory.SYSTEM):
    """Decorator to log function calls with timing"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.log(
                    LogLevel.INFO,
                    f"Function {func.__name__} completed successfully",
                    category,
                    {
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "args": str(args),
                        "kwargs": str(kwargs)
                    }
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.log(
                    LogLevel.ERROR,
                    f"Function {func.__name__} failed: {str(e)}",
                    category,
                    {
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                )
                raise
        return wrapper
    return decorator

# Initialize global logger
logger = StructuredLogger()

def log_error(
    error: Exception,
    method: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Log error with enhanced context and stack trace"""
    context = context or {}
    context.update({
        "method": method,
        "stack_trace": traceback.format_exc(),
        "error_type": type(error).__name__
    })
    
    logger.log(LogLevel.ERROR, str(error), LogCategory.SYSTEM, context)

def log_api_request(
    request_data: Dict[str, Any],
    response_data: Dict[str, Any],
    method: str,
    execution_time: float
) -> None:
    """Log API request details with enhanced tracking"""
    context = {
        "method": method,
        "request": request_data,
        "response": response_data,
        "execution_time": execution_time,
        "status_code": response_data.get("status_code", 200)
    }
    
    logger.log(LogLevel.INFO, f"API Request: {method}", LogCategory.SYSTEM, context)
