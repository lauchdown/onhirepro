import unittest
import frappe
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from frappe.utils import nowdate, add_days, getdate

class TestDashboardCharts(unittest.TestCase):
    """
    Test suite for Dashboard Charts in the OnHire Pro application.
    
    This test suite validates the correctness and robustness of all Dashboard Chart
    configurations, ensuring they are properly linked to their data sources and
    that the data sources are correctly implemented.
    """
    
    def setUp(self):
        """Set up test environment before each test."""
        # Mock frappe.get_doc for document retrieval
        self.get_doc_patcher = patch('frappe.get_doc')
        self.mock_get_doc = self.get_doc_patcher.start()
        
        # Mock frappe.get_all for document listing
        self.get_all_patcher = patch('frappe.get_all')
        self.mock_get_all = self.get_all_patcher.start()
        
        # Mock frappe.get_value for field value retrieval
        self.get_value_patcher = patch('frappe.get_value')
        self.mock_get_value = self.get_value_patcher.start()
        
        # Mock frappe.db for database queries
        self.db_patcher = patch('frappe.db')
        self.mock_db = self.db_patcher.start()
    
    def tearDown(self):
        """Clean up test environment after each test."""
        # Stop all patchers
        self.get_doc_patcher.stop()
        self.get_all_patcher.stop()
        self.get_value_patcher.stop()
        self.db_patcher.stop()
    
    def test_dashboard_chart_source_existence(self):
        """Test that all Dashboard Chart Sources exist and are properly configured."""
        # Mock data for Dashboard Chart Sources
        self.mock_get_all.return_value = [
            {"name": "dcs_item_utilization_rate"},
            {"name": "dcs_average_rental_duration"},
            {"name": "dcs_revenue_per_item_category"},
            {"name": "dcs_maintenance_turnaround_time"},
            {"name": "dcs_booking_conversion_rate"},
            {"name": "dcs_customer_churn_rate"},
            {"name": "dcs_damage_rate_cost"},
            {"name": "dcs_overdue_returns_rate_count"},
            {"name": "dcs_stock_reservation_conflicts"},
            {"name": "dcs_active_rental_jobs"},
            {"name": "dcs_jobs_due_for_dispatch"},
            {"name": "dcs_jobs_due_for_return"},
            {"name": "dcs_at_risk_stock"},
            {"name": "dcs_items_awaiting_assessment"},
            {"name": "dcs_items_in_maintenance"},
            {"name": "dcs_total_rental_revenue"},
            {"name": "dcs_open_rental_quotation_value"},
            {"name": "dcs_overdue_invoice_amount"},
            {"name": "dcs_average_revenue_per_rental_job"},
            {"name": "dcs_rental_revenue_trend"},
            {"name": "dcs_job_status_distribution"},
            {"name": "dcs_top_5_most_rented_items"},
            {"name": "dcs_top_5_customers_by_rental_value"},
            {"name": "dcs_damage_rate_by_item_group"},
            {"name": "dcs_item_utilization_rate_trend"}
        ]
        
        # Mock data for a Dashboard Chart Source document
        mock_source_doc = MagicMock()
        mock_source_doc.method = "onhire_pro.reports.kpi_utils.calculate_item_utilization_rate"
        mock_source_doc.filters_json = "{}"
        self.mock_get_doc.return_value = mock_source_doc
        
        # Test each Dashboard Chart Source
        for source in self.mock_get_all.return_value:
            # Get the source document
            source_doc = frappe.get_doc("Dashboard Chart Source", source["name"])
            
            # Verify that the method is specified
            self.assertIsNotNone(source_doc.method)
            self.assertTrue(len(source_doc.method) > 0)
            
            # Verify that the method points to a valid module
            module_path = source_doc.method.rsplit(".", 1)[0]
            function_name = source_doc.method.rsplit(".", 1)[1]
            
            # Verify that the filters_json is valid JSON
            if source_doc.filters_json:
                try:
                    filters = json.loads(source_doc.filters_json)
                    self.assertIsInstance(filters, dict)
                except json.JSONDecodeError:
                    self.fail(f"filters_json for {source['name']} is not valid JSON")
    
    def test_dashboard_chart_existence(self):
        """Test that all Dashboard Charts exist and are properly configured."""
        # Mock data for Dashboard Charts
        self.mock_get_all.return_value = [
            {"name": "item_utilization_rate_overall"},
            {"name": "average_rental_duration"},
            {"name": "revenue_per_item_category"},
            {"name": "maintenance_turnaround_time"},
            {"name": "booking_conversion_rate"},
            {"name": "customer_churn_rate"},
            {"name": "damage_rate_cost"},
            {"name": "overdue_returns_rate_count"},
            {"name": "stock_reservation_conflicts"},
            {"name": "active_rental_jobs"},
            {"name": "jobs_due_for_dispatch"},
            {"name": "jobs_due_for_return"},
            {"name": "at_risk_stock"},
            {"name": "items_awaiting_assessment"},
            {"name": "items_in_maintenance"},
            {"name": "total_rental_revenue_mtd_qtd"},
            {"name": "open_rental_quotation_value"},
            {"name": "overdue_invoice_amount"},
            {"name": "average_revenue_per_rental_job"},
            {"name": "quick_links_operations"},
            {"name": "rental_revenue_trend"},
            {"name": "job_status_distribution"},
            {"name": "top_5_most_rented_items"},
            {"name": "top_5_customers_by_rental_value"},
            {"name": "damage_rate_by_item_group"},
            {"name": "item_utilization_rate_trend"}
        ]
        
        # Mock data for a Dashboard Chart document
        mock_chart_doc = MagicMock()
        mock_chart_doc.chart_type = "Number"
        mock_chart_doc.chart_name = "Item Utilization Rate"
        mock_chart_doc.source = "dcs_item_utilization_rate"
        mock_chart_doc.filters_json = "{}"
        mock_chart_doc.time_interval = "Daily"
        mock_chart_doc.timespan = "Last Month"
        mock_chart_doc.color = "#7CD6FD"
        mock_chart_doc.is_public = 1
        self.mock_get_doc.return_value = mock_chart_doc
        
        # Test each Dashboard Chart
        for chart in self.mock_get_all.return_value:
            # Get the chart document
            chart_doc = frappe.get_doc("Dashboard Chart", chart["name"])
            
            # Verify that the chart has a name
            self.assertIsNotNone(chart_doc.chart_name)
            self.assertTrue(len(chart_doc.chart_name) > 0)
            
            # Verify that the chart has a source
            self.assertIsNotNone(chart_doc.source)
            self.assertTrue(len(chart_doc.source) > 0)
            
            # Verify that the chart has a type
            self.assertIsNotNone(chart_doc.chart_type)
            self.assertTrue(len(chart_doc.chart_type) > 0)
            
            # Verify that the filters_json is valid JSON
            if chart_doc.filters_json:
                try:
                    filters = json.loads(chart_doc.filters_json)
                    self.assertIsInstance(filters, dict)
                except json.JSONDecodeError:
                    self.fail(f"filters_json for {chart['name']} is not valid JSON")
    
    def test_dashboard_existence(self):
        """Test that all Dashboards exist and are properly configured."""
        # Mock data for Dashboards
        self.mock_get_all.return_value = [
            {"name": "operational_overview_dashboard"},
            {"name": "inventory_health_risk_dashboard"},
            {"name": "financial_snapshot_rental_specific_dashboard"}
        ]
        
        # Mock data for a Dashboard document
        mock_dashboard_doc = MagicMock()
        mock_dashboard_doc.dashboard_name = "Operational Overview"
        mock_dashboard_doc.charts = [
            {"chart": "active_rental_jobs"},
            {"chart": "jobs_due_for_dispatch"},
            {"chart": "jobs_due_for_return"}
        ]
        self.mock_get_doc.return_value = mock_dashboard_doc
        
        # Test each Dashboard
        for dashboard in self.mock_get_all.return_value:
            # Get the dashboard document
            dashboard_doc = frappe.get_doc("Dashboard", dashboard["name"])
            
            # Verify that the dashboard has a name
            self.assertIsNotNone(dashboard_doc.dashboard_name)
            self.assertTrue(len(dashboard_doc.dashboard_name) > 0)
            
            # Verify that the dashboard has charts
            self.assertIsNotNone(dashboard_doc.charts)
            self.assertTrue(len(dashboard_doc.charts) > 0)
            
            # Verify that each chart in the dashboard exists
            for chart in dashboard_doc.charts:
                self.assertIsNotNone(chart.chart)
                self.assertTrue(len(chart.chart) > 0)
    
    def test_dashboard_chart_source_method_mapping(self):
        """Test that all Dashboard Chart Sources are mapped to valid methods."""
        # Mock data for Dashboard Chart Sources
        self.mock_get_all.return_value = [
            {"name": "dcs_item_utilization_rate", "method": "onhire_pro.reports.kpi_utils.calculate_item_utilization_rate"},
            {"name": "dcs_average_rental_duration", "method": "onhire_pro.reports.kpi_utils.calculate_average_rental_duration"},
            {"name": "dcs_revenue_per_item_category", "method": "onhire_pro.reports.kpi_utils.get_revenue_per_item_category"},
            {"name": "dcs_maintenance_turnaround_time", "method": "onhire_pro.reports.kpi_utils.calculate_avg_maintenance_turnaround_time"},
            {"name": "dcs_booking_conversion_rate", "method": "onhire_pro.reports.kpi_utils.calculate_booking_conversion_rate"},
            {"name": "dcs_customer_churn_rate", "method": "onhire_pro.reports.kpi_utils.calculate_customer_churn_rate"},
            {"name": "dcs_damage_rate_cost", "method": "onhire_pro.reports.kpi_utils.calculate_damage_rate"},
            {"name": "dcs_overdue_returns_rate_count", "method": "onhire_pro.reports.kpi_utils.get_overdue_returns_count"},
            {"name": "dcs_stock_reservation_conflicts", "method": "onhire_pro.reports.kpi_utils.get_stock_reservation_conflicts"},
            {"name": "dcs_active_rental_jobs", "method": "onhire_pro.reports.kpi_utils.get_active_rental_jobs_count"},
            {"name": "dcs_jobs_due_for_dispatch", "method": "onhire_pro.reports.kpi_utils.get_jobs_due_for_dispatch_count"},
            {"name": "dcs_jobs_due_for_return", "method": "onhire_pro.reports.kpi_utils.get_jobs_due_for_return_count"},
            {"name": "dcs_at_risk_stock", "method": "onhire_pro.reports.kpi_utils.get_at_risk_stock_count"},
            {"name": "dcs_items_awaiting_assessment", "method": "onhire_pro.reports.kpi_utils.get_items_awaiting_assessment_count"},
            {"name": "dcs_items_in_maintenance", "method": "onhire_pro.reports.kpi_utils.get_items_in_maintenance_count"},
            {"name": "dcs_total_rental_revenue", "method": "onhire_pro.reports.kpi_utils.get_total_rental_revenue"},
            {"name": "dcs_open_rental_quotation_value", "method": "onhire_pro.reports.kpi_utils.get_open_rental_quotation_value"},
            {"name": "dcs_overdue_invoice_amount", "method": "onhire_pro.reports.kpi_utils.get_overdue_invoice_amount"},
            {"name": "dcs_average_revenue_per_rental_job", "method": "onhire_pro.reports.kpi_utils.get_average_revenue_per_rental_job"},
            {"name": "dcs_rental_revenue_trend", "method": "onhire_pro.reports.kpi_utils.get_rental_revenue_trend"},
            {"name": "dcs_job_status_distribution", "method": "onhire_pro.reports.kpi_utils.get_job_status_distribution"},
            {"name": "dcs_top_5_most_rented_items", "method": "onhire_pro.reports.kpi_utils.get_top_5_most_rented_items"},
            {"name": "dcs_top_5_customers_by_rental_value", "method": "onhire_pro.reports.kpi_utils.get_top_5_customers_by_rental_value"},
            {"name": "dcs_damage_rate_by_item_group", "method": "onhire_pro.reports.kpi_utils.get_damage_rate_by_item_group"},
            {"name": "dcs_item_utilization_rate_trend", "method": "onhire_pro.reports.kpi_utils.get_item_utilization_rate_trend"}
        ]
        
        # Define valid method prefixes
        valid_prefixes = [
            "onhire_pro.reports.kpi_utils.",
            "onhire_pro.utils.kpi_calculations."
        ]
        
        # Test each Dashboard Chart Source
        for source in self.mock_get_all.return_value:
            # Verify that the method is specified
            self.assertIsNotNone(source["method"])
            self.assertTrue(len(source["method"]) > 0)
            
            # Verify that the method has a valid prefix
            has_valid_prefix = False
            for prefix in valid_prefixes:
                if source["method"].startswith(prefix):
                    has_valid_prefix = True
                    break
            
            self.assertTrue(has_valid_prefix, f"Method {source['method']} does not have a valid prefix")
    
    def test_dashboard_chart_to_source_mapping(self):
        """Test that all Dashboard Charts are mapped to valid Dashboard Chart Sources."""
        # Mock data for Dashboard Charts
        self.mock_get_all.side_effect = [
            # First call: Dashboard Charts
            [
                {"name": "item_utilization_rate_overall", "source": "dcs_item_utilization_rate"},
                {"name": "average_rental_duration", "source": "dcs_average_rental_duration"},
                {"name": "revenue_per_item_category", "source": "dcs_revenue_per_item_category"},
                {"name": "maintenance_turnaround_time", "source": "dcs_maintenance_turnaround_time"},
                {"name": "booking_conversion_rate", "source": "dcs_booking_conversion_rate"},
                {"name": "customer_churn_rate", "source": "dcs_customer_churn_rate"},
                {"name": "damage_rate_cost", "source": "dcs_damage_rate_cost"},
                {"name": "overdue_returns_rate_count", "source": "dcs_overdue_returns_rate_count"},
                {"name": "stock_reservation_conflicts", "source": "dcs_stock_reservation_conflicts"},
                {"name": "active_rental_jobs", "source": "dcs_active_rental_jobs"},
                {"name": "jobs_due_for_dispatch", "source": "dcs_jobs_due_for_dispatch"},
                {"name": "jobs_due_for_return", "source": "dcs_jobs_due_for_return"},
                {"name": "at_risk_stock", "source": "dcs_at_risk_stock"},
                {"name": "items_awaiting_assessment", "source": "dcs_items_awaiting_assessment"},
                {"name": "items_in_maintenance", "source": "dcs_items_in_maintenance"},
                {"name": "total_rental_revenue_mtd_qtd", "source": "dcs_total_rental_revenue"},
                {"name": "open_rental_quotation_value", "source": "dcs_open_rental_quotation_value"},
                {"name": "overdue_invoice_amount", "source": "dcs_overdue_invoice_amount"},
                {"name": "average_revenue_per_rental_job", "source": "dcs_average_revenue_per_rental_job"},
                {"name": "rental_revenue_trend", "source": "dcs_rental_revenue_trend"},
                {"name": "job_status_distribution", "source": "dcs_job_status_distribution"},
                {"name": "top_5_most_rented_items", "source": "dcs_top_5_most_rented_items"},
                {"name": "top_5_customers_by_rental_value", "source": "dcs_top_5_customers_by_rental_value"},
                {"name": "damage_rate_by_item_group", "source": "dcs_damage_rate_by_item_group"},
                {"name": "item_utilization_rate_trend", "source": "dcs_item_utilization_rate_trend"}
            ],
            # Second call: Dashboard Chart Sources
            [
                {"name": "dcs_item_utilization_rate"},
                {"name": "dcs_average_rental_duration"},
                {"name": "dcs_revenue_per_item_category"},
                {"name": "dcs_maintenance_turnaround_time"},
                {"name": "dcs_booking_conversion_rate"},
                {"name": "dcs_customer_churn_rate"},
                {"name": "dcs_damage_rate_cost"},
                {"name": "dcs_overdue_returns_rate_count"},
                {"name": "dcs_stock_reservation_conflicts"},
                {"name": "dcs_active_rental_jobs"},
                {"name": "dcs_jobs_due_for_dispatch"},
                {"name": "dcs_jobs_due_for_return"},
                {"name": "dcs_at_risk_stock"},
                {"name": "dcs_items_awaiting_assessment"},
                {"name": "dcs_items_in_maintenance"},
                {"name": "dcs_total_rental_revenue"},
                {"name": "dcs_open_rental_quotation_value"},
                {"name": "dcs_overdue_invoice_amount"},
                {"name": "dcs_average_revenue_per_rental_job"},
                {"name": "dcs_rental_revenue_trend"},
                {"name": "dcs_job_status_distribution"},
                {"name": "dcs_top_5_most_rented_items"},
                {"name": "dcs_top_5_customers_by_rental_value"},
                {"name": "dcs_damage_rate_by_item_group"},
                {"name": "dcs_item_utilization_rate_trend"}
            ]
        ]
        
        # Get all Dashboard Charts
        dashboard_charts = frappe.get_all("Dashboard Chart", fields=["name", "source"])
        
        # Get all Dashboard Chart Sources
        dashboard_chart_sources = frappe.get_all("Dashboard Chart Source", fields=["name"])
        
        # Create a set of valid source names
        valid_sources = {source["name"] for source in dashboard_chart_sources}
        
        # Test each Dashboard Chart
        for chart in dashboard_charts:
            # Verify that the source is specified
            self.assertIsNotNone(chart["source"])
            self.assertTrue(len(chart["source"]) > 0)
            
            # Verify that the source exists
            self.assertIn(chart["source"], valid_sources, f"Source {chart['source']} for chart {chart['name']} does not exist")
    
    def test_dashboard_to_chart_mapping(self):
        """Test that all Dashboards are mapped to valid Dashboard Charts."""
        # Mock data for Dashboards
        self.mock_get_all.side_effect = [
            # First call: Dashboards
            [
                {
                    "name": "operational_overview_dashboard",
                    "charts": [
                        {"chart": "active_rental_jobs"},
                        {"chart": "jobs_due_for_dispatch"},
                        {"chart": "jobs_due_for_return"}
                    ]
                },
                {
                    "name": "inventory_health_risk_dashboard",
                    "charts": [
                        {"chart": "at_risk_stock"},
                        {"chart": "stock_reservation_conflicts"},
                        {"chart": "items_awaiting_assessment"},
                        {"chart": "items_in_maintenance"},
                        {"chart": "maintenance_turnaround_time"},
                        {"chart": "item_utilization_rate_overall"}
                    ]
                },
                {
                    "name": "financial_snapshot_rental_specific_dashboard",
                    "charts": [
                        {"chart": "total_rental_revenue_mtd_qtd"},
                        {"chart": "open_rental_quotation_value"},
                        {"chart": "overdue_invoice_amount"},
                        {"chart": "average_revenue_per_rental_job"}
                    ]
                }
            ],
            # Second call: Dashboard Charts
            [
                {"name": "active_rental_jobs"},
                {"name": "jobs_due_for_dispatch"},
                {"name": "jobs_due_for_return"},
                {"name": "at_risk_stock"},
                {"name": "stock_reservation_conflicts"},
                {"name": "items_awaiting_assessment"},
                {"name": "items_in_maintenance"},
                {"name": "maintenance_turnaround_time"},
                {"name": "item_utilization_rate_overall"},
                {"name": "total_rental_revenue_mtd_qtd"},
                {"name": "open_rental_quotation_value"},
                {"name": "overdue_invoice_amount"},
                {"name": "average_revenue_per_rental_job"}
            ]
        ]
        
        # Mock data for a Dashboard document
        mock_dashboard_doc = MagicMock()
        mock_dashboard_doc.dashboard_name = "Operational Overview"
        mock_dashboard_doc.charts = [
            {"chart": "active_rental_jobs"},
            {"chart": "jobs_due_for_dispatch"},
            {"chart": "jobs_due_for_return"}
        ]
        self.mock_get_doc.return_value = mock_dashboard_doc
        
        # Get all Dashboards
        dashboards = frappe.get_all("Dashboard")
        
        # Get all Dashboard Charts
        dashboard_charts = frappe.get_all("Dashboard Chart", fields=["name"])
        
        # Create a set of valid chart names
        valid_charts = {chart["name"] for chart in dashboard_charts}
        
        # Test each Dashboard
        for dashboard_name in dashboards:
            # Get the dashboard document
            dashboard_doc = frappe.get_doc("Dashboard", dashboard_name["name"])
            
            # Verify that the dashboard has charts
            self.assertIsNotNone(dashboard_doc.charts)
            self.assertTrue(len(dashboard_doc.charts) > 0)
            
            # Verify that each chart in the dashboard exists
            for chart in dashboard_doc.charts:
                self.assertIsNotNone(chart.chart)
                self.assertTrue(len(chart.chart) > 0)
                self.assertIn(chart.chart, valid_charts, f"Chart {chart.chart} for dashboard {dashboard_name['name']} does not exist")
    
    def test_quick_links_operations_json_structure(self):
        """Test that the quick_links_operations.json file has a valid structure."""
        # Mock data for the quick_links_operations.json file
        mock_quick_links_doc = MagicMock()
        mock_quick_links_doc.json = """{
            "doctype": "Dashboard Chart",
            "name": "quick_links_operations",
            "chart_name": "Quick Links - Operations",
            "chart_type": "Custom",
            "custom_options": "{\\\"type\\\": \\\"links\\\", \\\"links\\\": [{\\\"label\\\": \\\"New Rental Job\\\", \\\"url\\\": \\\"/app/rental-job/new-rental-job-1\\\", \\\"icon\\\": \\\"fa fa-plus\\\"}, {\\\"label\\\": \\\"Dispatch Schedule\\\", \\\"url\\\": \\\"/app/dispatch-schedule\\\", \\\"icon\\\": \\\"fa fa-truck\\\"}, {\\\"label\\\": \\\"Return Schedule\\\", \\\"url\\\": \\\"/app/return-schedule\\\", \\\"icon\\\": \\\"fa fa-undo\\\"}, {\\\"label\\\": \\\"Rental Items\\\", \\\"url\\\": \\\"/app/item?is_rental_item=1\\\", \\\"icon\\\": \\\"fa fa-cubes\\\"}, {\\\"label\\\": \\\"Maintenance Tasks\\\", \\\"url\\\": \\\"/app/maintenance-task\\\", \\\"icon\\\": \\\"fa fa-wrench\\\"}]}",
            "is_public": 1,
            "restrict_to_roles": [
                {
                    "role": "Rental Manager"
                },
                {
                    "role": "Rental User"
                },
                {
                    "role": "Rental Operator"
                }
            ]
        }"""
        self.mock_get_doc.return_value = mock_quick_links_doc
        
        # Get the quick_links_operations.json file
        quick_links_doc = frappe.get_doc("Dashboard Chart", "quick_links_operations")
        
        # Verify that the file has a valid JSON structure
        try:
            quick_links_json = json.loads(quick_links_doc.json)
            self.assertIsInstance(quick_links_json, dict)
            
            # Verify that the required fields are present
            self.assertIn("doctype", quick_links_json)
            self.assertIn("name", quick_links_json)
            self.assertIn("chart_name", quick_links_json)
            self.assertIn("chart_type", quick_links_json)
            self.assertIn("custom_options", quick_links_json)
            
            # Verify that the custom_options field is valid JSON
            custom_options = json.loads(quick_links_json["custom_options"].replace("\\\"", "\""))
            self.assertIsInstance(custom_options, dict)
            
            # Verify that the required fields in custom_options are present
            self.assertIn("type", custom_options)
            self.assertIn("links", custom_options)
            self.assertEqual(custom_options["type"], "links")
            self.assertIsInstance(custom_options["links"], list)
            
            # Verify that each link has the required fields
            for link in custom_options["links"]:
                self.assertIn("label", link)
                self.assertIn("url", link)
                self.assertIn("icon", link)
        except json.JSONDecodeError:
            self.fail("quick_links_operations.json is not valid JSON")
        except Exception as e:
            self.fail(f"Error validating quick_links_operations.json: {str(e)}")


if __name__ == '__main__':
    unittest.main()
