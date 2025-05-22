"""
OnHire Pro - Rental Management Application for ERPNext

This module provides schema verification utilities for the OnHire Pro application.
These functions are used to verify the existence and structure of custom fields
and doctypes required by the KPI calculation functions.

Error handling is implemented throughout to ensure robustness in production.
"""

import frappe
import json
import logging
from typing import Dict, List, Optional, Union, Any

# Configure logger
logger = logging.getLogger(__name__)

class SchemaVerificationError(Exception):
    """Exception raised for schema verification errors."""
    pass

def verify_doctype_exists(doctype_name: str) -> bool:
    """
    Verify that a doctype exists in the system.
    
    Args:
        doctype_name (str): Name of the doctype to verify
        
    Returns:
        bool: True if the doctype exists, False otherwise
        
    Example:
        >>> verify_doctype_exists("Rental Job")
        True
    """
    try:
        return frappe.db.exists("DocType", doctype_name) is not None
    except Exception as e:
        logger.error(f"Error verifying doctype existence for {doctype_name}: {str(e)}")
        return False

def verify_field_exists(doctype_name: str, field_name: str) -> bool:
    """
    Verify that a field exists in a doctype.
    
    Args:
        doctype_name (str): Name of the doctype
        field_name (str): Name of the field to verify
        
    Returns:
        bool: True if the field exists, False otherwise
        
    Example:
        >>> verify_field_exists("Rental Job", "status")
        True
    """
    try:
        if not verify_doctype_exists(doctype_name):
            return False
            
        meta = frappe.get_meta(doctype_name)
        return meta.has_field(field_name)
    except Exception as e:
        logger.error(f"Error verifying field existence for {doctype_name}.{field_name}: {str(e)}")
        return False

def verify_field_type(doctype_name: str, field_name: str, expected_type: str) -> bool:
    """
    Verify that a field in a doctype is of the expected type.
    
    Args:
        doctype_name (str): Name of the doctype
        field_name (str): Name of the field to verify
        expected_type (str): Expected field type
        
    Returns:
        bool: True if the field is of the expected type, False otherwise
        
    Example:
        >>> verify_field_type("Rental Job", "status", "Select")
        True
    """
    try:
        if not verify_field_exists(doctype_name, field_name):
            return False
            
        meta = frappe.get_meta(doctype_name)
        field = meta.get_field(field_name)
        return field.fieldtype == expected_type
    except Exception as e:
        logger.error(f"Error verifying field type for {doctype_name}.{field_name}: {str(e)}")
        return False

def verify_schema_requirements(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify that all schema requirements are met.
    
    Args:
        requirements (dict): Dictionary of schema requirements
            Format: {
                "doctypes": [
                    {"name": "DocType1", "required": True},
                    {"name": "DocType2", "required": False}
                ],
                "fields": [
                    {"doctype": "DocType1", "name": "field1", "type": "Data", "required": True},
                    {"doctype": "DocType2", "name": "field2", "type": "Select", "required": False}
                ]
            }
        
    Returns:
        dict: Dictionary with verification results
            Format: {
                "success": bool,
                "missing_doctypes": [str],
                "missing_fields": [{"doctype": str, "field": str}],
                "wrong_type_fields": [{"doctype": str, "field": str, "expected": str, "actual": str}]
            }
        
    Example:
        >>> requirements = {
        ...     "doctypes": [
        ...         {"name": "Rental Job", "required": True},
        ...         {"name": "Rental Job Item", "required": True}
        ...     ],
        ...     "fields": [
        ...         {"doctype": "Rental Job", "name": "status", "type": "Select", "required": True},
        ...         {"doctype": "Rental Job Item", "name": "item_code", "type": "Link", "required": True}
        ...     ]
        ... }
        >>> verify_schema_requirements(requirements)
        {'success': True, 'missing_doctypes': [], 'missing_fields': [], 'wrong_type_fields': []}
    """
    result = {
        "success": True,
        "missing_doctypes": [],
        "missing_fields": [],
        "wrong_type_fields": []
    }
    
    try:
        # Verify doctypes
        for doctype in requirements.get("doctypes", []):
            doctype_name = doctype.get("name")
            required = doctype.get("required", True)
            
            if not verify_doctype_exists(doctype_name):
                result["missing_doctypes"].append(doctype_name)
                if required:
                    result["success"] = False
        
        # Verify fields
        for field in requirements.get("fields", []):
            doctype_name = field.get("doctype")
            field_name = field.get("name")
            field_type = field.get("type")
            required = field.get("required", True)
            
            # Skip if doctype doesn't exist
            if doctype_name in result["missing_doctypes"]:
                continue
                
            # Check field existence
            if not verify_field_exists(doctype_name, field_name):
                result["missing_fields"].append({"doctype": doctype_name, "field": field_name})
                if required:
                    result["success"] = False
                continue
                
            # Check field type
            if field_type and not verify_field_type(doctype_name, field_name, field_type):
                meta = frappe.get_meta(doctype_name)
                actual_type = meta.get_field(field_name).fieldtype
                result["wrong_type_fields"].append({
                    "doctype": doctype_name,
                    "field": field_name,
                    "expected": field_type,
                    "actual": actual_type
                })
                if required:
                    result["success"] = False
    
    except Exception as e:
        logger.error(f"Error verifying schema requirements: {str(e)}")
        result["success"] = False
        result["error"] = str(e)
    
    return result

def load_schema_requirements_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load schema requirements from a JSON file.
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        dict: Dictionary of schema requirements
        
    Raises:
        SchemaVerificationError: If the file cannot be loaded or is invalid
        
    Example:
        >>> load_schema_requirements_from_file("/path/to/requirements.json")
        {'doctypes': [...], 'fields': [...]}
    """
    try:
        with open(file_path, 'r') as f:
            requirements = json.load(f)
            
        # Validate requirements format
        if not isinstance(requirements, dict):
            raise SchemaVerificationError("Requirements must be a dictionary")
            
        if "doctypes" not in requirements or not isinstance(requirements["doctypes"], list):
            raise SchemaVerificationError("Requirements must contain a 'doctypes' list")
            
        if "fields" not in requirements or not isinstance(requirements["fields"], list):
            raise SchemaVerificationError("Requirements must contain a 'fields' list")
            
        return requirements
    
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {str(e)}")
        raise SchemaVerificationError(f"Invalid JSON in requirements file: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error loading schema requirements from {file_path}: {str(e)}")
        raise SchemaVerificationError(f"Error loading schema requirements: {str(e)}")

def get_rental_schema_requirements() -> Dict[str, Any]:
    """
    Get the schema requirements for the rental management application.
    
    Returns:
        dict: Dictionary of schema requirements
        
    Example:
        >>> get_rental_schema_requirements()
        {'doctypes': [...], 'fields': [...]}
    """
    return {
        "doctypes": [
            {"name": "Rental Job", "required": True},
            {"name": "Rental Job Item", "required": True},
            {"name": "Item", "required": True},
            {"name": "Bin", "required": True},
            {"name": "Sales Invoice", "required": True},
            {"name": "Quotation", "required": True},
            {"name": "Customer", "required": True},
            {"name": "Maintenance Task", "required": False},
            {"name": "Condition Assessment", "required": False}
        ],
        "fields": [
            # Rental Job fields
            {"doctype": "Rental Job", "name": "status", "type": "Select", "required": True},
            {"doctype": "Rental Job", "name": "company", "type": "Link", "required": True},
            {"doctype": "Rental Job", "name": "customer", "type": "Link", "required": True},
            {"doctype": "Rental Job", "name": "start_date", "type": "Date", "required": True},
            {"doctype": "Rental Job", "name": "end_date", "type": "Date", "required": True},
            {"doctype": "Rental Job", "name": "has_damaged_items", "type": "Check", "required": False},
            {"doctype": "Rental Job", "name": "quotation", "type": "Link", "required": False},
            
            # Rental Job Item fields
            {"doctype": "Rental Job Item", "name": "item_code", "type": "Link", "required": True},
            {"doctype": "Rental Job Item", "name": "warehouse", "type": "Link", "required": True},
            {"doctype": "Rental Job Item", "name": "qty", "type": "Float", "required": True},
            {"doctype": "Rental Job Item", "name": "amount", "type": "Currency", "required": True},
            {"doctype": "Rental Job Item", "name": "start_date", "type": "Date", "required": True},
            {"doctype": "Rental Job Item", "name": "end_date", "type": "Date", "required": True},
            
            # Item fields
            {"doctype": "Item", "name": "item_name", "type": "Data", "required": True},
            {"doctype": "Item", "name": "item_group", "type": "Link", "required": True},
            {"doctype": "Item", "name": "is_rental_item", "type": "Check", "required": True},
            
            # Bin fields
            {"doctype": "Bin", "name": "item_code", "type": "Link", "required": True},
            {"doctype": "Bin", "name": "warehouse", "type": "Link", "required": True},
            {"doctype": "Bin", "name": "actual_qty", "type": "Float", "required": True},
            
            # Sales Invoice fields
            {"doctype": "Sales Invoice", "name": "posting_date", "type": "Date", "required": True},
            {"doctype": "Sales Invoice", "name": "grand_total", "type": "Currency", "required": True},
            {"doctype": "Sales Invoice", "name": "outstanding_amount", "type": "Currency", "required": True},
            {"doctype": "Sales Invoice", "name": "due_date", "type": "Date", "required": True},
            {"doctype": "Sales Invoice", "name": "rental_job", "type": "Link", "required": False},
            
            # Quotation fields
            {"doctype": "Quotation", "name": "transaction_date", "type": "Date", "required": True},
            {"doctype": "Quotation", "name": "valid_till", "type": "Date", "required": True},
            {"doctype": "Quotation", "name": "grand_total", "type": "Currency", "required": True},
            {"doctype": "Quotation", "name": "rental_quotation", "type": "Check", "required": False},
            
            # Customer fields
            {"doctype": "Customer", "name": "customer_name", "type": "Data", "required": True},
            
            # Maintenance Task fields
            {"doctype": "Maintenance Task", "name": "status", "type": "Select", "required": False},
            {"doctype": "Maintenance Task", "name": "start_date", "type": "Date", "required": False},
            {"doctype": "Maintenance Task", "name": "completion_date", "type": "Date", "required": False},
            
            # Condition Assessment fields
            {"doctype": "Condition Assessment", "name": "status", "type": "Select", "required": False}
        ]
    }

def verify_kpi_schema_requirements() -> Dict[str, Any]:
    """
    Verify that all schema requirements for KPI calculations are met.
    
    Returns:
        dict: Dictionary with verification results
        
    Example:
        >>> verify_kpi_schema_requirements()
        {'success': True, 'missing_doctypes': [], 'missing_fields': [], 'wrong_type_fields': []}
    """
    requirements = get_rental_schema_requirements()
    return verify_schema_requirements(requirements)

def log_schema_verification_results(results: Dict[str, Any]) -> None:
    """
    Log the results of schema verification.
    
    Args:
        results (dict): Dictionary with verification results
        
    Example:
        >>> results = verify_kpi_schema_requirements()
        >>> log_schema_verification_results(results)
    """
    if results["success"]:
        logger.info("Schema verification successful")
    else:
        logger.warning("Schema verification failed")
        
        if results["missing_doctypes"]:
            logger.warning(f"Missing doctypes: {', '.join(results['missing_doctypes'])}")
            
        if results["missing_fields"]:
            missing_fields = [f"{f['doctype']}.{f['field']}" for f in results["missing_fields"]]
            logger.warning(f"Missing fields: {', '.join(missing_fields)}")
            
        if results["wrong_type_fields"]:
            wrong_types = [
                f"{f['doctype']}.{f['field']} (expected: {f['expected']}, actual: {f['actual']})"
                for f in results["wrong_type_fields"]
            ]
            logger.warning(f"Fields with wrong type: {', '.join(wrong_types)}")
