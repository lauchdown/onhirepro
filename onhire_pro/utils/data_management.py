"""
Advanced data export and import system with validation, transformation, and error handling
"""
import frappe
import json
import csv
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
import pandas as pd
from io import StringIO, BytesIO
from .logger import logger, LogCategory, LogLevel
from .error_handler import OnHireProError, log_error

class DataFormat:
    CSV = 'csv'
    JSON = 'json'
    XLSX = 'xlsx'

class DataValidator:
    """Validate data structure and content"""
    
    @staticmethod
    def validate_schema(doctype: str, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate data against DocType schema"""
        try:
            meta = frappe.get_meta(doctype)
            errors = []
            
            # Check required fields
            for field in meta.get_mandatory_fields():
                if field.fieldname not in data or not data[field.fieldname]:
                    errors.append(f"Missing required field: {field.fieldname}")
            
            # Validate field types
            for field_name, value in data.items():
                field = meta.get_field(field_name)
                if not field:
                    continue
                
                try:
                    # Type validation based on fieldtype
                    if field.fieldtype == "Int" and not isinstance(value, (int, float)):
                        errors.append(f"Invalid integer value for {field_name}: {value}")
                    elif field.fieldtype == "Float" and not isinstance(value, (int, float)):
                        errors.append(f"Invalid float value for {field_name}: {value}")
                    elif field.fieldtype == "Date":
                        datetime.strptime(str(value), '%Y-%m-%d')
                    elif field.fieldtype == "Link":
                        if not frappe.db.exists(field.options, value):
                            errors.append(f"Invalid link value for {field_name}: {value}")
                except ValueError:
                    errors.append(f"Invalid value for {field_name}: {value}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            log_error(e, "Schema Validation Error")
            return False, [str(e)]

    @staticmethod
    def sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize data to prevent injection and ensure data integrity"""
        sanitized = {}
        for key, value in data.items():
            # Handle different types of data
            if isinstance(value, str):
                # Remove potential SQL injection characters
                sanitized[key] = frappe.db.escape(value.strip())
            elif isinstance(value, (int, float)):
                sanitized[key] = value
            elif isinstance(value, list):
                sanitized[key] = [
                    frappe.db.escape(str(v).strip()) if isinstance(v, str) else v 
                    for v in value
                ]
            elif isinstance(value, dict):
                sanitized[key] = DataValidator.sanitize_data(value)
            else:
                sanitized[key] = value
        return sanitized

class DataTransformer:
    """Transform data between different formats"""
    
    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> str:
        """Convert data to CSV format"""
        if not data:
            return ""
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    
    @staticmethod
    def from_csv(content: str) -> List[Dict[str, Any]]:
        """Parse CSV content to data structure"""
        input_file = StringIO(content)
        reader = csv.DictReader(input_file)
        return [{k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
                for row in reader]
    
    @staticmethod
    def to_json(data: List[Dict[str, Any]]) -> str:
        """Convert data to JSON format"""
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def from_json(content: str) -> List[Dict[str, Any]]:
        """Parse JSON content to data structure"""
        return json.loads(content)
    
    @staticmethod
    def to_xlsx(data: List[Dict[str, Any]]) -> bytes:
        """Convert data to Excel format"""
        df = pd.DataFrame(data)
        output = BytesIO()
        df.to_excel(output, index=False)
        return output.getvalue()
    
    @staticmethod
    def from_xlsx(content: bytes) -> List[Dict[str, Any]]:
        """Parse Excel content to data structure"""
        df = pd.read_excel(content)
        return df.to_dict('records')

class DataManager:
    """Manage data export and import operations"""
    
    def __init__(self):
        self.validator = DataValidator()
        self.transformer = DataTransformer()
        self.supported_formats = [DataFormat.CSV, DataFormat.JSON, DataFormat.XLSX]
    
    def export_data(
        self,
        doctype: str,
        filters: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        file_format: str = DataFormat.CSV,
        batch_size: int = 1000
    ) -> Union[str, bytes]:
        """Export data with batching and progress tracking"""
        try:
            if file_format not in self.supported_formats:
                raise OnHireProError(f"Unsupported format: {file_format}")
            
            logger.log(
                LogLevel.INFO,
                f"Starting data export for {doctype}",
                LogCategory.SYSTEM,
                {"format": file_format, "filters": filters}
            )
            
            # Get total count
            total_count = frappe.db.count(doctype, filters)
            processed = 0
            all_data = []
            
            # Process in batches
            while processed < total_count:
                batch = frappe.get_all(
                    doctype,
                    filters=filters,
                    fields=fields or ['*'],
                    limit_start=processed,
                    limit_page_length=batch_size
                )
                
                all_data.extend(batch)
                processed += len(batch)
                
                # Log progress
                logger.log(
                    LogLevel.INFO,
                    f"Export progress: {processed}/{total_count}",
                    LogCategory.SYSTEM
                )
            
            # Transform to requested format
            if file_format == DataFormat.CSV:
                return self.transformer.to_csv(all_data)
            elif file_format == DataFormat.JSON:
                return self.transformer.to_json(all_data)
            else:  # xlsx
                return self.transformer.to_xlsx(all_data)
                
        except Exception as e:
            log_error(e, "Data Export Error")
            raise OnHireProError("Failed to export data", {"error": str(e)})
    
    def import_data(
        self,
        doctype: str,
        file_content: Union[str, bytes],
        file_format: str = DataFormat.CSV,
        validate_only: bool = False
    ) -> Dict[str, Any]:
        """Import data with validation and error handling"""
        try:
            if file_format not in self.supported_formats:
                raise OnHireProError(f"Unsupported format: {file_format}")
            
            # Parse data based on format
            if file_format == DataFormat.CSV:
                data = self.transformer.from_csv(file_content)
            elif file_format == DataFormat.JSON:
                data = self.transformer.from_json(file_content)
            else:  # xlsx
                data = self.transformer.from_xlsx(file_content)
            
            results = {
                "success": [],
                "errors": [],
                "total": len(data)
            }
            
            # Process each record
            for index, record in enumerate(data):
                try:
                    # Validate record
                    is_valid, errors = self.validator.validate_schema(doctype, record)
                    if not is_valid:
                        results["errors"].append({
                            "row": index + 1,
                            "errors": errors
                        })
                        continue
                    
                    # Sanitize data
                    sanitized_record = self.validator.sanitize_data(record)
                    
                    if not validate_only:
                        # Import record
                        doc = frappe.get_doc({
                            "doctype": doctype,
                            **sanitized_record
                        })
                        doc.insert()
                        results["success"].append(doc.name)
                        
                except Exception as e:
                    results["errors"].append({
                        "row": index + 1,
                        "error": str(e)
                    })
            
            # Log import results
            logger.log(
                LogLevel.INFO,
                f"Data import completed for {doctype}",
                LogCategory.SYSTEM,
                {
                    "total": results["total"],
                    "success": len(results["success"]),
                    "errors": len(results["errors"])
                }
            )
            
            return results
            
        except Exception as e:
            log_error(e, "Data Import Error")
            raise OnHireProError("Failed to import data", {"error": str(e)})
    
    def export_to_file(
        self,
        doctype: str,
        filepath: str,
        filters: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None
    ) -> None:
        """Export data to file"""
        try:
            # Determine format from file extension
            file_format = filepath.split('.')[-1].lower()
            if file_format not in self.supported_formats:
                raise OnHireProError(f"Unsupported file format: {file_format}")
            
            # Export data
            data = self.export_data(
                doctype,
                filters=filters,
                fields=fields,
                file_format=file_format
            )
            
            # Write to file
            mode = 'wb' if isinstance(data, bytes) else 'w'
            with open(filepath, mode) as f:
                f.write(data)
                
            logger.log(
                LogLevel.INFO,
                f"Data exported to file: {filepath}",
                LogCategory.SYSTEM,
                {"doctype": doctype}
            )
            
        except Exception as e:
            log_error(e, "File Export Error")
            raise OnHireProError("Failed to export to file", {"error": str(e)})
    
    def import_from_file(
        self,
        doctype: str,
        filepath: str,
        validate_only: bool = False
    ) -> Dict[str, Any]:
        """Import data from file"""
        try:
            # Determine format from file extension
            file_format = filepath.split('.')[-1].lower()
            if file_format not in self.supported_formats:
                raise OnHireProError(f"Unsupported file format: {file_format}")
            
            # Read file content
            mode = 'rb' if file_format == DataFormat.XLSX else 'r'
            with open(filepath, mode) as f:
                content = f.read()
            
            # Import data
            return self.import_data(
                doctype,
                content,
                file_format=file_format,
                validate_only=validate_only
            )
            
        except Exception as e:
            log_error(e, "File Import Error")
            raise OnHireProError("Failed to import from file", {"error": str(e)})

# Initialize global data manager
data_manager = DataManager()

# Example usage functions
def export_rental_data(
    filters: Optional[Dict[str, Any]] = None,
    file_format: str = DataFormat.CSV
) -> Union[str, bytes]:
    """Export rental data with enhanced filtering"""
    try:
        return data_manager.export_data(
            "Rental Order",
            filters=filters,
            fields=[
                'name', 'customer', 'status', 'start_date',
                'end_date', 'total_amount', 'items'
            ],
            file_format=file_format
        )
    except Exception as e:
        log_error(e, "Rental Data Export Error")
        raise OnHireProError("Failed to export rental data", {"error": str(e)})

def import_rental_data(
    file_content: Union[str, bytes],
    file_format: str = DataFormat.CSV
) -> Dict[str, Any]:
    """Import rental data with validation"""
    try:
        return data_manager.import_data(
            "Rental Order",
            file_content,
            file_format=file_format
        )
    except Exception as e:
        log_error(e, "Rental Data Import Error")
        raise OnHireProError("Failed to import rental data", {"error": str(e)})
