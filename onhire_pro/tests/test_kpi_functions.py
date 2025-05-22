import unittest
import frappe
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from frappe.utils import nowdate, add_days, getdate

# Import the KPI utility functions to test
from onhire_pro.reports.kpi_utils import (
    calculate_item_utilization_rate,
    calculate_average_rental_duration,
    get_revenue_per_item_category,
    calculate_avg_maintenance_turnaround_time,
    calculate_booking_conversion_rate,
    calculate_customer_churn_rate,
    calculate_damage_rate,
    get_stock_reservation_conflicts,
    get_overdue_returns_count,
    get_active_rental_jobs_count,
    get_total_rental_revenue
)

class TestKPIFunctions(unittest.TestCase):
    """
    Test suite for KPI utility functions in the OnHire Pro application.
    
    This test suite validates the correctness and robustness of all KPI calculation
    functions used in dashboards and reports. It includes tests for:
    - Input validation
    - Error handling
    - Calculation logic
    - Edge cases
    """
    
    def setUp(self):
        """Set up test environment before each test."""
        # Common test data
        self.company = "Test Company"
        self.today = nowdate()
        self.yesterday = add_days(self.today, -1)
        self.last_week = add_days(self.today, -7)
        self.last_month = add_days(self.today, -30)
        
        # Default filters
        self.default_filters = {
            "company": self.company,
            "from_date": self.last_month,
            "to_date": self.today
        }
        
        # Mock frappe.db for database queries
        self.db_patcher = patch('frappe.db')
        self.mock_db = self.db_patcher.start()
        
        # Mock frappe.get_doc for document retrieval
        self.get_doc_patcher = patch('frappe.get_doc')
        self.mock_get_doc = self.get_doc_patcher.start()
        
        # Mock frappe.get_all for document listing
        self.get_all_patcher = patch('frappe.get_all')
        self.mock_get_all = self.get_all_patcher.start()
        
        # Mock frappe.get_value for field value retrieval
        self.get_value_patcher = patch('frappe.get_value')
        self.mock_get_value = self.get_value_patcher.start()
        
        # Mock frappe.get_cached_value for cached field value retrieval
        self.get_cached_value_patcher = patch('frappe.get_cached_value')
        self.mock_get_cached_value = self.get_cached_value_patcher.start()
        
        # Mock frappe.get_list for document listing
        self.get_list_patcher = patch('frappe.get_list')
        self.mock_get_list = self.get_list_patcher.start()
        
        # Mock frappe.get_single for single doctype retrieval
        self.get_single_patcher = patch('frappe.get_single')
        self.mock_get_single = self.get_single_patcher.start()
        
        # Mock frappe.db.sql for direct SQL queries
        self.mock_db.sql = MagicMock()
        
        # Mock frappe.db.get_value for field value retrieval
        self.mock_db.get_value = MagicMock()
        
        # Mock frappe.db.get_list for document listing
        self.mock_db.get_list = MagicMock()
        
        # Mock frappe.db.get_all for document listing
        self.mock_db.get_all = MagicMock()
        
        # Mock frappe.db.exists for document existence check
        self.mock_db.exists = MagicMock()
        
        # Mock frappe.db.count for document counting
        self.mock_db.count = MagicMock()
        
        # Mock frappe.db.get_single_value for single doctype field value
        self.mock_db.get_single_value = MagicMock()
    
    def tearDown(self):
        """Clean up test environment after each test."""
        # Stop all patchers
        self.db_patcher.stop()
        self.get_doc_patcher.stop()
        self.get_all_patcher.stop()
        self.get_value_patcher.stop()
        self.get_cached_value_patcher.stop()
        self.get_list_patcher.stop()
        self.get_single_patcher.stop()
    
    def test_calculate_item_utilization_rate_basic(self):
        """Test basic functionality of item utilization rate calculation."""
        # Mock data for total rental days
        self.mock_db.sql.return_value = [(100,)]  # 100 total rental days
        
        # Mock data for total available days
        self.mock_db.get_all.return_value = [
            {"name": "ITEM001", "creation": "2023-01-01"},
            {"name": "ITEM002", "creation": "2023-01-15"}
        ]
        
        # Calculate days between creation and today for each item
        today = datetime.strptime(self.today, "%Y-%m-%d")
        item1_days = (today - datetime.strptime("2023-01-01", "%Y-%m-%d")).days
        item2_days = (today - datetime.strptime("2023-01-15", "%Y-%m-%d")).days
        total_available_days = item1_days + item2_days
        
        # Expected utilization rate
        expected_rate = (100 / total_available_days) * 100
        
        # Call the function
        result = calculate_item_utilization_rate(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertAlmostEqual(result["value"], expected_rate, places=2)
    
    def test_calculate_item_utilization_rate_no_items(self):
        """Test item utilization rate calculation with no items."""
        # Mock data for total rental days
        self.mock_db.sql.return_value = [(0,)]  # 0 total rental days
        
        # Mock data for total available days (no items)
        self.mock_db.get_all.return_value = []
        
        # Call the function
        result = calculate_item_utilization_rate(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_calculate_item_utilization_rate_missing_filters(self):
        """Test item utilization rate calculation with missing filters."""
        # Call the function with missing company
        result = calculate_item_utilization_rate({"from_date": self.last_month, "to_date": self.today})
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
        
        # Call the function with missing date range
        result = calculate_item_utilization_rate({"company": self.company})
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_calculate_average_rental_duration_basic(self):
        """Test basic functionality of average rental duration calculation."""
        # Mock data for rental durations
        self.mock_db.sql.return_value = [
            {"rental_duration": 5},
            {"rental_duration": 10},
            {"rental_duration": 15}
        ]
        
        # Expected average duration
        expected_avg = (5 + 10 + 15) / 3
        
        # Call the function
        result = calculate_average_rental_duration(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], expected_avg)
    
    def test_calculate_average_rental_duration_no_rentals(self):
        """Test average rental duration calculation with no rentals."""
        # Mock data for rental durations (no rentals)
        self.mock_db.sql.return_value = []
        
        # Call the function
        result = calculate_average_rental_duration(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_get_revenue_per_item_category_basic(self):
        """Test basic functionality of revenue per item category calculation."""
        # Mock data for item categories and revenue
        self.mock_db.sql.return_value = [
            {"item_group": "Category A", "total_revenue": 1000},
            {"item_group": "Category B", "total_revenue": 2000},
            {"item_group": "Category C", "total_revenue": 3000}
        ]
        
        # Call the function
        result = get_revenue_per_item_category(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("labels", result)
        self.assertIn("datasets", result)
        self.assertEqual(len(result["labels"]), 3)
        self.assertEqual(len(result["datasets"][0]["values"]), 3)
        self.assertEqual(result["datasets"][0]["values"][0], 1000)
        self.assertEqual(result["datasets"][0]["values"][1], 2000)
        self.assertEqual(result["datasets"][0]["values"][2], 3000)
    
    def test_get_revenue_per_item_category_no_revenue(self):
        """Test revenue per item category calculation with no revenue."""
        # Mock data for item categories and revenue (no revenue)
        self.mock_db.sql.return_value = []
        
        # Call the function
        result = get_revenue_per_item_category(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("labels", result)
        self.assertIn("datasets", result)
        self.assertEqual(len(result["labels"]), 0)
        self.assertEqual(len(result["datasets"][0]["values"]), 0)
    
    def test_calculate_avg_maintenance_turnaround_time_basic(self):
        """Test basic functionality of average maintenance turnaround time calculation."""
        # Mock data for maintenance tasks
        self.mock_db.sql.return_value = [
            {"turnaround_time": 2},
            {"turnaround_time": 3},
            {"turnaround_time": 4}
        ]
        
        # Expected average turnaround time
        expected_avg = (2 + 3 + 4) / 3
        
        # Call the function
        result = calculate_avg_maintenance_turnaround_time(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], expected_avg)
    
    def test_calculate_avg_maintenance_turnaround_time_no_tasks(self):
        """Test average maintenance turnaround time calculation with no tasks."""
        # Mock data for maintenance tasks (no tasks)
        self.mock_db.sql.return_value = []
        
        # Call the function
        result = calculate_avg_maintenance_turnaround_time(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_calculate_booking_conversion_rate_basic(self):
        """Test basic functionality of booking conversion rate calculation."""
        # Mock data for quotations and rental jobs
        self.mock_db.count.side_effect = [10, 5]  # 10 quotations, 5 converted to rental jobs
        
        # Expected conversion rate
        expected_rate = (5 / 10) * 100
        
        # Call the function
        result = calculate_booking_conversion_rate(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], expected_rate)
    
    def test_calculate_booking_conversion_rate_no_quotations(self):
        """Test booking conversion rate calculation with no quotations."""
        # Mock data for quotations and rental jobs (no quotations)
        self.mock_db.count.side_effect = [0, 0]  # 0 quotations, 0 converted to rental jobs
        
        # Call the function
        result = calculate_booking_conversion_rate(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_calculate_customer_churn_rate_basic(self):
        """Test basic functionality of customer churn rate calculation."""
        # Mock data for customers at start, end, and new customers
        self.mock_db.sql.side_effect = [
            [(10,)],  # 10 customers at start
            [(12,)],  # 12 customers at end
            [(5,)]    # 5 new customers
        ]
        
        # Expected churn rate
        # Customers lost = (Start + New) - End = (10 + 5) - 12 = 3
        # Churn rate = (Customers lost / Start) * 100 = (3 / 10) * 100 = 30%
        expected_rate = 30
        
        # Call the function
        result = calculate_customer_churn_rate(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], expected_rate)
    
    def test_calculate_customer_churn_rate_no_customers(self):
        """Test customer churn rate calculation with no customers."""
        # Mock data for customers at start, end, and new customers (no customers)
        self.mock_db.sql.side_effect = [
            [(0,)],  # 0 customers at start
            [(0,)],  # 0 customers at end
            [(0,)]   # 0 new customers
        ]
        
        # Call the function
        result = calculate_customer_churn_rate(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_calculate_damage_rate_basic(self):
        """Test basic functionality of damage rate calculation."""
        # Mock data for total rentals and damaged rentals
        self.mock_db.count.side_effect = [100, 10]  # 100 total rentals, 10 damaged
        
        # Expected damage rate
        expected_rate = (10 / 100) * 100
        
        # Call the function
        result = calculate_damage_rate(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], expected_rate)
    
    def test_calculate_damage_rate_no_rentals(self):
        """Test damage rate calculation with no rentals."""
        # Mock data for total rentals and damaged rentals (no rentals)
        self.mock_db.count.side_effect = [0, 0]  # 0 total rentals, 0 damaged
        
        # Call the function
        result = calculate_damage_rate(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_get_stock_reservation_conflicts_basic(self):
        """Test basic functionality of stock reservation conflicts calculation."""
        # Mock data for stock reservation conflicts
        self.mock_db.sql.return_value = [
            {"item_code": "ITEM001", "warehouse": "Warehouse A", "conflicts": 2},
            {"item_code": "ITEM002", "warehouse": "Warehouse B", "conflicts": 3}
        ]
        
        # Call the function
        result = get_stock_reservation_conflicts(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 5)  # Total conflicts: 2 + 3 = 5
    
    def test_get_stock_reservation_conflicts_no_conflicts(self):
        """Test stock reservation conflicts calculation with no conflicts."""
        # Mock data for stock reservation conflicts (no conflicts)
        self.mock_db.sql.return_value = []
        
        # Call the function
        result = get_stock_reservation_conflicts(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_get_overdue_returns_count_basic(self):
        """Test basic functionality of overdue returns count calculation."""
        # Mock data for overdue returns
        self.mock_db.count.return_value = 5  # 5 overdue returns
        
        # Call the function
        result = get_overdue_returns_count(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 5)
    
    def test_get_overdue_returns_count_no_overdue(self):
        """Test overdue returns count calculation with no overdue returns."""
        # Mock data for overdue returns (no overdue)
        self.mock_db.count.return_value = 0  # 0 overdue returns
        
        # Call the function
        result = get_overdue_returns_count(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_get_active_rental_jobs_count_basic(self):
        """Test basic functionality of active rental jobs count calculation."""
        # Mock data for active rental jobs
        self.mock_db.count.return_value = 8  # 8 active rental jobs
        
        # Call the function
        result = get_active_rental_jobs_count(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 8)
    
    def test_get_active_rental_jobs_count_no_active(self):
        """Test active rental jobs count calculation with no active jobs."""
        # Mock data for active rental jobs (no active)
        self.mock_db.count.return_value = 0  # 0 active rental jobs
        
        # Call the function
        result = get_active_rental_jobs_count(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_get_total_rental_revenue_basic(self):
        """Test basic functionality of total rental revenue calculation."""
        # Mock data for total rental revenue
        self.mock_db.sql.return_value = [(5000,)]  # $5000 total revenue
        
        # Call the function
        result = get_total_rental_revenue(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 5000)
    
    def test_get_total_rental_revenue_no_revenue(self):
        """Test total rental revenue calculation with no revenue."""
        # Mock data for total rental revenue (no revenue)
        self.mock_db.sql.return_value = [(0,)]  # $0 total revenue
        
        # Call the function
        result = get_total_rental_revenue(self.default_filters)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("value", result)
        self.assertEqual(result["value"], 0)
    
    def test_error_handling_in_all_functions(self):
        """Test error handling in all KPI functions."""
        # Make the database queries raise exceptions
        self.mock_db.sql.side_effect = Exception("Database error")
        self.mock_db.count.side_effect = Exception("Database error")
        self.mock_db.get_all.side_effect = Exception("Database error")
        
        # Test all functions
        functions_to_test = [
            calculate_item_utilization_rate,
            calculate_average_rental_duration,
            get_revenue_per_item_category,
            calculate_avg_maintenance_turnaround_time,
            calculate_booking_conversion_rate,
            calculate_customer_churn_rate,
            calculate_damage_rate,
            get_stock_reservation_conflicts,
            get_overdue_returns_count,
            get_active_rental_jobs_count,
            get_total_rental_revenue
        ]
        
        for func in functions_to_test:
            # Call the function
            result = func(self.default_filters)
            
            # Verify the result
            self.assertIsInstance(result, dict)
            self.assertIn("value", result)
            
            # Functions should return a default value (usually 0) on error
            if func == get_revenue_per_item_category:
                self.assertEqual(len(result["labels"]), 0)
                self.assertEqual(len(result["datasets"][0]["values"]), 0)
            else:
                self.assertEqual(result["value"], 0)


if __name__ == '__main__':
    unittest.main()
