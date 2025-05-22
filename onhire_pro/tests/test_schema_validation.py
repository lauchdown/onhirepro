import unittest
import frappe
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from frappe.utils import nowdate, add_days, getdate

# Import the schema verification utility
from onhire_pro.utils.schema_verifier import (
    verify_doctype_exists,
    verify_field_exists,
    verify_field_type,
    verify_schema_requirements
)

class TestSchemaValidation(unittest.TestCase):
    """
    Test suite for schema validation in the OnHire Pro application.
    
    This test suite validates the correctness and robustness of the schema
    verification utilities and ensures that all required custom schemas
    are properly defined and accessible.
    """
    
    def setUp(self):
        """Set up test environment before each test."""
        # Mock frappe.db for database queries
        self.db_patcher = patch('frappe.db')
        self.mock_db = self.db_patcher.start()
        
        # Mock frappe.get_meta for metadata retrieval
        self.get_meta_patcher = patch('frappe.get_meta')
        self.mock_get_meta = self.get_meta_patcher.start()
        
        # Mock frappe.get_doc for document retrieval
        self.get_doc_patcher = patch('frappe.get_doc')
        self.mock_get_doc = self.get_doc_patcher.start()
        
        # Mock frappe.get_all for document listing
        self.get_all_patcher = patch('frappe.get_all')
        self.mock_get_all = self.get_all_patcher.start()
    
    def tearDown(self):
        """Clean up test environment after each test."""
        # Stop all patchers
        self.db_patcher.stop()
        self.get_meta_patcher.stop()
        self.get_doc_patcher.stop()
        self.get_all_patcher.stop()
    
    def test_verify_doctype_exists(self):
        """Test that the verify_doctype_exists function works correctly."""
        # Mock data for doctype existence
        self.mock_db.exists.side_effect = [True, False]
        
        # Test with existing doctype
        result = verify_doctype_exists("Rental Job")
        self.assertTrue(result)
        
        # Test with non-existing doctype
        result = verify_doctype_exists("Non Existent Doctype")
        self.assertFalse(result)
    
    def test_verify_field_exists(self):
        """Test that the verify_field_exists function works correctly."""
        # Mock data for field existence
        mock_meta = MagicMock()
        mock_meta.get_field.side_effect = [MagicMock(), None]
        self.mock_get_meta.return_value = mock_meta
        
        # Test with existing field
        result = verify_field_exists("Rental Job", "status")
        self.assertTrue(result)
        
        # Test with non-existing field
        result = verify_field_exists("Rental Job", "non_existent_field")
        self.assertFalse(result)
    
    def test_verify_field_type(self):
        """Test that the verify_field_type function works correctly."""
        # Mock data for field type
        mock_field_1 = MagicMock()
        mock_field_1.fieldtype = "Data"
        
        mock_field_2 = MagicMock()
        mock_field_2.fieldtype = "Select"
        
        mock_meta = MagicMock()
        mock_meta.get_field.side_effect = [mock_field_1, mock_field_2, None]
        self.mock_get_meta.return_value = mock_meta
        
        # Test with correct field type
        result = verify_field_type("Rental Job", "status", "Data")
        self.assertTrue(result)
        
        # Test with incorrect field type
        result = verify_field_type("Rental Job", "status", "Link")
        self.assertFalse(result)
        
        # Test with non-existing field
        result = verify_field_type("Rental Job", "non_existent_field", "Data")
        self.assertFalse(result)
    
    def test_verify_schema_requirements(self):
        """Test that the verify_schema_requirements function works correctly."""
        # Mock data for schema requirements
        self.mock_db.exists.return_value = True
        
        mock_field_1 = MagicMock()
        mock_field_1.fieldtype = "Data"
        
        mock_field_2 = MagicMock()
        mock_field_2.fieldtype = "Select"
        
        mock_field_3 = MagicMock()
        mock_field_3.fieldtype = "Link"
        mock_field_3.options = "Item"
        
        mock_meta = MagicMock()
        mock_meta.get_field.side_effect = [mock_field_1, mock_field_2, mock_field_3, None]
        self.mock_get_meta.return_value = mock_meta
        
        # Define schema requirements
        schema_requirements = {
            "Rental Job": {
                "fields": {
                    "status": {"type": "Data"},
                    "rental_type": {"type": "Select"},
                    "item": {"type": "Link", "options": "Item"},
                    "non_existent_field": {"type": "Data"}
                }
            }
        }
        
        # Test schema requirements
        result = verify_schema_requirements(schema_requirements)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("Rental Job", result)
        self.assertIn("fields", result["Rental Job"])
        self.assertIn("status", result["Rental Job"]["fields"])
        self.assertIn("rental_type", result["Rental Job"]["fields"])
        self.assertIn("item", result["Rental Job"]["fields"])
        self.assertIn("non_existent_field", result["Rental Job"]["fields"])
        
        self.assertTrue(result["Rental Job"]["fields"]["status"]["exists"])
        self.assertTrue(result["Rental Job"]["fields"]["status"]["type_match"])
        
        self.assertTrue(result["Rental Job"]["fields"]["rental_type"]["exists"])
        self.assertTrue(result["Rental Job"]["fields"]["rental_type"]["type_match"])
        
        self.assertTrue(result["Rental Job"]["fields"]["item"]["exists"])
        self.assertTrue(result["Rental Job"]["fields"]["item"]["type_match"])
        
        self.assertFalse(result["Rental Job"]["fields"]["non_existent_field"]["exists"])
        self.assertFalse(result["Rental Job"]["fields"]["non_existent_field"]["type_match"])
    
    def test_rental_job_schema(self):
        """Test that the Rental Job schema is correctly defined."""
        # Mock data for Rental Job schema
        self.mock_db.exists.return_value = True
        
        mock_status_field = MagicMock()
        mock_status_field.fieldtype = "Select"
        mock_status_field.options = "Draft\nConfirmed\nIn Progress\nCompleted\nCancelled"
        
        mock_start_date_field = MagicMock()
        mock_start_date_field.fieldtype = "Date"
        
        mock_end_date_field = MagicMock()
        mock_end_date_field.fieldtype = "Date"
        
        mock_customer_field = MagicMock()
        mock_customer_field.fieldtype = "Link"
        mock_customer_field.options = "Customer"
        
        mock_items_field = MagicMock()
        mock_items_field.fieldtype = "Table"
        mock_items_field.options = "Rental Job Item"
        
        mock_meta = MagicMock()
        mock_meta.get_field.side_effect = [
            mock_status_field,
            mock_start_date_field,
            mock_end_date_field,
            mock_customer_field,
            mock_items_field
        ]
        self.mock_get_meta.return_value = mock_meta
        
        # Define schema requirements for Rental Job
        schema_requirements = {
            "Rental Job": {
                "fields": {
                    "status": {"type": "Select", "options": "Draft\nConfirmed\nIn Progress\nCompleted\nCancelled"},
                    "start_date": {"type": "Date"},
                    "end_date": {"type": "Date"},
                    "customer": {"type": "Link", "options": "Customer"},
                    "items": {"type": "Table", "options": "Rental Job Item"}
                }
            }
        }
        
        # Test Rental Job schema
        result = verify_schema_requirements(schema_requirements)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("Rental Job", result)
        self.assertIn("fields", result["Rental Job"])
        
        for field_name in ["status", "start_date", "end_date", "customer", "items"]:
            self.assertIn(field_name, result["Rental Job"]["fields"])
            self.assertTrue(result["Rental Job"]["fields"][field_name]["exists"])
            self.assertTrue(result["Rental Job"]["fields"][field_name]["type_match"])
    
    def test_rental_job_item_schema(self):
        """Test that the Rental Job Item schema is correctly defined."""
        # Mock data for Rental Job Item schema
        self.mock_db.exists.return_value = True
        
        mock_item_code_field = MagicMock()
        mock_item_code_field.fieldtype = "Link"
        mock_item_code_field.options = "Item"
        
        mock_qty_field = MagicMock()
        mock_qty_field.fieldtype = "Float"
        
        mock_rate_field = MagicMock()
        mock_rate_field.fieldtype = "Currency"
        
        mock_amount_field = MagicMock()
        mock_amount_field.fieldtype = "Currency"
        
        mock_parent_field = MagicMock()
        mock_parent_field.fieldtype = "Link"
        mock_parent_field.options = "Rental Job"
        
        mock_meta = MagicMock()
        mock_meta.get_field.side_effect = [
            mock_item_code_field,
            mock_qty_field,
            mock_rate_field,
            mock_amount_field,
            mock_parent_field
        ]
        self.mock_get_meta.return_value = mock_meta
        
        # Define schema requirements for Rental Job Item
        schema_requirements = {
            "Rental Job Item": {
                "fields": {
                    "item_code": {"type": "Link", "options": "Item"},
                    "qty": {"type": "Float"},
                    "rate": {"type": "Currency"},
                    "amount": {"type": "Currency"},
                    "parent": {"type": "Link", "options": "Rental Job"}
                }
            }
        }
        
        # Test Rental Job Item schema
        result = verify_schema_requirements(schema_requirements)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("Rental Job Item", result)
        self.assertIn("fields", result["Rental Job Item"])
        
        for field_name in ["item_code", "qty", "rate", "amount", "parent"]:
            self.assertIn(field_name, result["Rental Job Item"]["fields"])
            self.assertTrue(result["Rental Job Item"]["fields"][field_name]["exists"])
            self.assertTrue(result["Rental Job Item"]["fields"][field_name]["type_match"])
    
    def test_maintenance_task_schema(self):
        """Test that the Maintenance Task schema is correctly defined."""
        # Mock data for Maintenance Task schema
        self.mock_db.exists.return_value = True
        
        mock_item_field = MagicMock()
        mock_item_field.fieldtype = "Link"
        mock_item_field.options = "Item"
        
        mock_status_field = MagicMock()
        mock_status_field.fieldtype = "Select"
        mock_status_field.options = "Pending\nIn Progress\nCompleted\nCancelled"
        
        mock_start_date_field = MagicMock()
        mock_start_date_field.fieldtype = "Date"
        
        mock_end_date_field = MagicMock()
        mock_end_date_field.fieldtype = "Date"
        
        mock_description_field = MagicMock()
        mock_description_field.fieldtype = "Text"
        
        mock_meta = MagicMock()
        mock_meta.get_field.side_effect = [
            mock_item_field,
            mock_status_field,
            mock_start_date_field,
            mock_end_date_field,
            mock_description_field
        ]
        self.mock_get_meta.return_value = mock_meta
        
        # Define schema requirements for Maintenance Task
        schema_requirements = {
            "Maintenance Task": {
                "fields": {
                    "item": {"type": "Link", "options": "Item"},
                    "status": {"type": "Select", "options": "Pending\nIn Progress\nCompleted\nCancelled"},
                    "start_date": {"type": "Date"},
                    "end_date": {"type": "Date"},
                    "description": {"type": "Text"}
                }
            }
        }
        
        # Test Maintenance Task schema
        result = verify_schema_requirements(schema_requirements)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("Maintenance Task", result)
        self.assertIn("fields", result["Maintenance Task"])
        
        for field_name in ["item", "status", "start_date", "end_date", "description"]:
            self.assertIn(field_name, result["Maintenance Task"]["fields"])
            self.assertTrue(result["Maintenance Task"]["fields"][field_name]["exists"])
            self.assertTrue(result["Maintenance Task"]["fields"][field_name]["type_match"])
    
    def test_condition_assessment_schema(self):
        """Test that the Condition Assessment schema is correctly defined."""
        # Mock data for Condition Assessment schema
        self.mock_db.exists.return_value = True
        
        mock_item_field = MagicMock()
        mock_item_field.fieldtype = "Link"
        mock_item_field.options = "Item"
        
        mock_status_field = MagicMock()
        mock_status_field.fieldtype = "Select"
        mock_status_field.options = "Pending Pre-Rental\nPending Post-Rental\nCompleted\nCancelled"
        
        mock_assessment_date_field = MagicMock()
        mock_assessment_date_field.fieldtype = "Date"
        
        mock_condition_field = MagicMock()
        mock_condition_field.fieldtype = "Select"
        mock_condition_field.options = "Excellent\nGood\nFair\nPoor\nDamaged"
        
        mock_notes_field = MagicMock()
        mock_notes_field.fieldtype = "Text"
        
        mock_meta = MagicMock()
        mock_meta.get_field.side_effect = [
            mock_item_field,
            mock_status_field,
            mock_assessment_date_field,
            mock_condition_field,
            mock_notes_field
        ]
        self.mock_get_meta.return_value = mock_meta
        
        # Define schema requirements for Condition Assessment
        schema_requirements = {
            "Condition Assessment": {
                "fields": {
                    "item": {"type": "Link", "options": "Item"},
                    "status": {"type": "Select", "options": "Pending Pre-Rental\nPending Post-Rental\nCompleted\nCancelled"},
                    "assessment_date": {"type": "Date"},
                    "condition": {"type": "Select", "options": "Excellent\nGood\nFair\nPoor\nDamaged"},
                    "notes": {"type": "Text"}
                }
            }
        }
        
        # Test Condition Assessment schema
        result = verify_schema_requirements(schema_requirements)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("Condition Assessment", result)
        self.assertIn("fields", result["Condition Assessment"])
        
        for field_name in ["item", "status", "assessment_date", "condition", "notes"]:
            self.assertIn(field_name, result["Condition Assessment"]["fields"])
            self.assertTrue(result["Condition Assessment"]["fields"][field_name]["exists"])
            self.assertTrue(result["Condition Assessment"]["fields"][field_name]["type_match"])
    
    def test_forecasted_kpi_value_schema(self):
        """Test that the Forecasted KPI Value schema is correctly defined."""
        # Mock data for Forecasted KPI Value schema
        self.mock_db.exists.return_value = True
        
        mock_kpi_name_field = MagicMock()
        mock_kpi_name_field.fieldtype = "Data"
        
        mock_forecast_date_field = MagicMock()
        mock_forecast_date_field.fieldtype = "Date"
        
        mock_target_date_field = MagicMock()
        mock_target_date_field.fieldtype = "Date"
        
        mock_forecasted_value_field = MagicMock()
        mock_forecasted_value_field.fieldtype = "Float"
        
        mock_lower_bound_field = MagicMock()
        mock_lower_bound_field.fieldtype = "Float"
        
        mock_upper_bound_field = MagicMock()
        mock_upper_bound_field.fieldtype = "Float"
        
        mock_algorithm_field = MagicMock()
        mock_algorithm_field.fieldtype = "Select"
        mock_algorithm_field.options = "Prophet\nARIMA\nExponential Smoothing"
        
        mock_company_field = MagicMock()
        mock_company_field.fieldtype = "Link"
        mock_company_field.options = "Company"
        
        mock_meta = MagicMock()
        mock_meta.get_field.side_effect = [
            mock_kpi_name_field,
            mock_forecast_date_field,
            mock_target_date_field,
            mock_forecasted_value_field,
            mock_lower_bound_field,
            mock_upper_bound_field,
            mock_algorithm_field,
            mock_company_field
        ]
        self.mock_get_meta.return_value = mock_meta
        
        # Define schema requirements for Forecasted KPI Value
        schema_requirements = {
            "Forecasted KPI Value": {
                "fields": {
                    "kpi_name": {"type": "Data"},
                    "forecast_date": {"type": "Date"},
                    "target_date": {"type": "Date"},
                    "forecasted_value": {"type": "Float"},
                    "lower_bound": {"type": "Float"},
                    "upper_bound": {"type": "Float"},
                    "algorithm": {"type": "Select", "options": "Prophet\nARIMA\nExponential Smoothing"},
                    "company": {"type": "Link", "options": "Company"}
                }
            }
        }
        
        # Test Forecasted KPI Value schema
        result = verify_schema_requirements(schema_requirements)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("Forecasted KPI Value", result)
        self.assertIn("fields", result["Forecasted KPI Value"])
        
        for field_name in ["kpi_name", "forecast_date", "target_date", "forecasted_value", "lower_bound", "upper_bound", "algorithm", "company"]:
            self.assertIn(field_name, result["Forecasted KPI Value"]["fields"])
            self.assertTrue(result["Forecasted KPI Value"]["fields"][field_name]["exists"])
            self.assertTrue(result["Forecasted KPI Value"]["fields"][field_name]["type_match"])


if __name__ == '__main__':
    unittest.main()
