import frappe
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from frappe.utils import nowdate, add_days, getdate, add_months, get_datetime
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

class KPIDataCollector:
    """
    Class for collecting historical KPI data for forecasting purposes.
    
    This class provides methods to collect, store, and retrieve historical KPI data
    for use in forecasting models. It supports collecting data for multiple KPIs
    across different time periods and companies.
    """
    
    def __init__(self, company=None):
        """
        Initialize the KPI data collector.
        
        Args:
            company (str, optional): Company to collect data for. If not specified,
                                    uses the default company from user preferences.
        """
        self.company = company or frappe.defaults.get_user_default("company")
        self.kpi_functions = {
            "item_utilization_rate": calculate_item_utilization_rate,
            "average_rental_duration": calculate_average_rental_duration,
            "revenue_per_item_category": get_revenue_per_item_category,
            "maintenance_turnaround_time": calculate_avg_maintenance_turnaround_time,
            "booking_conversion_rate": calculate_booking_conversion_rate,
            "customer_churn_rate": calculate_customer_churn_rate,
            "damage_rate": calculate_damage_rate,
            "stock_reservation_conflicts": get_stock_reservation_conflicts,
            "overdue_returns_count": get_overdue_returns_count,
            "active_rental_jobs_count": get_active_rental_jobs_count,
            "total_rental_revenue": get_total_rental_revenue
        }
        
        # KPIs suitable for forecasting as identified in requirements
        self.forecastable_kpis = [
            "item_utilization_rate",
            "total_rental_revenue",
            "booking_conversion_rate",
            "average_rental_duration",
            "maintenance_turnaround_time"
        ]
    
    def collect_kpi_data_for_date(self, kpi_name, date, filters=None):
        """
        Collect KPI data for a specific date.
        
        Args:
            kpi_name (str): Name of the KPI to collect data for
            date (str): Date to collect data for (YYYY-MM-DD format)
            filters (dict, optional): Additional filters to apply to the KPI calculation
            
        Returns:
            float: The KPI value for the specified date
        """
        if kpi_name not in self.kpi_functions:
            frappe.log_error(
                f"Unknown KPI: {kpi_name}",
                "KPI Data Collection Error"
            )
            return None
        
        # Prepare filters
        if not filters:
            filters = {}
        
        # Add company and date filters
        filters["company"] = self.company
        filters["from_date"] = date
        filters["to_date"] = date
        
        try:
            # Call the appropriate KPI function
            result = self.kpi_functions[kpi_name](filters)
            
            # Extract the value from the result
            if isinstance(result, dict) and "value" in result:
                value = result["value"]
            else:
                frappe.log_error(
                    f"Unexpected result format for KPI {kpi_name}: {result}",
                    "KPI Data Collection Error"
                )
                return None
            
            # Store the collected data
            self._store_historical_kpi_value(kpi_name, date, value, filters)
            
            return value
        except Exception as e:
            frappe.log_error(
                f"Error collecting data for KPI {kpi_name} on {date}: {str(e)}\n{frappe.get_traceback()}",
                "KPI Data Collection Error"
            )
            return None
    
    def collect_kpi_data_for_period(self, kpi_name, start_date, end_date, filters=None):
        """
        Collect KPI data for a period of time.
        
        Args:
            kpi_name (str): Name of the KPI to collect data for
            start_date (str): Start date of the period (YYYY-MM-DD format)
            end_date (str): End date of the period (YYYY-MM-DD format)
            filters (dict, optional): Additional filters to apply to the KPI calculation
            
        Returns:
            pandas.DataFrame: DataFrame with dates and KPI values
        """
        start_date = getdate(start_date)
        end_date = getdate(end_date)
        
        # Create a date range
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date.strftime("%Y-%m-%d"))
            current_date = add_days(current_date, 1)
        
        # Collect data for each date
        values = []
        for date in dates:
            value = self.collect_kpi_data_for_date(kpi_name, date, filters)
            values.append(value)
        
        # Create a DataFrame
        df = pd.DataFrame({
            "date": pd.to_datetime(dates),
            "value": values
        })
        
        return df
    
    def collect_all_kpi_data_for_period(self, start_date, end_date, filters=None):
        """
        Collect data for all forecastable KPIs for a period of time.
        
        Args:
            start_date (str): Start date of the period (YYYY-MM-DD format)
            end_date (str): End date of the period (YYYY-MM-DD format)
            filters (dict, optional): Additional filters to apply to the KPI calculation
            
        Returns:
            dict: Dictionary with KPI names as keys and DataFrames as values
        """
        result = {}
        
        for kpi_name in self.forecastable_kpis:
            df = self.collect_kpi_data_for_period(kpi_name, start_date, end_date, filters)
            result[kpi_name] = df
        
        return result
    
    def _store_historical_kpi_value(self, kpi_name, date, value, filters):
        """
        Store a historical KPI value in the database.
        
        Args:
            kpi_name (str): Name of the KPI
            date (str): Date of the KPI value (YYYY-MM-DD format)
            value (float): The KPI value
            filters (dict): Filters used to calculate the value
            
        Returns:
            str: Name of the created/updated document
        """
        try:
            # Check if a record already exists for this KPI, date, and company
            existing = frappe.db.exists(
                "Historical KPI Value",
                {
                    "kpi_name": kpi_name,
                    "date": date,
                    "company": self.company
                }
            )
            
            if existing:
                # Update existing record
                doc = frappe.get_doc("Historical KPI Value", existing)
                doc.actual_value = value
                doc.filters_json = json.dumps(filters)
                doc.save()
                return doc.name
            else:
                # Create new record
                doc = frappe.new_doc("Historical KPI Value")
                doc.kpi_name = kpi_name
                doc.date = date
                doc.actual_value = value
                doc.company = self.company
                doc.filters_json = json.dumps(filters)
                doc.insert()
                return doc.name
        except Exception as e:
            frappe.log_error(
                f"Error storing historical KPI value for {kpi_name} on {date}: {str(e)}\n{frappe.get_traceback()}",
                "KPI Data Storage Error"
            )
            return None
    
    def get_historical_kpi_data(self, kpi_name, start_date, end_date):
        """
        Retrieve historical KPI data from the database.
        
        Args:
            kpi_name (str): Name of the KPI to retrieve data for
            start_date (str): Start date of the period (YYYY-MM-DD format)
            end_date (str): End date of the period (YYYY-MM-DD format)
            
        Returns:
            pandas.DataFrame: DataFrame with dates and KPI values
        """
        try:
            # Query the database for historical KPI values
            data = frappe.db.get_all(
                "Historical KPI Value",
                filters={
                    "kpi_name": kpi_name,
                    "date": ["between", [start_date, end_date]],
                    "company": self.company
                },
                fields=["date", "actual_value"],
                order_by="date"
            )
            
            if not data:
                return pd.DataFrame(columns=["date", "value"])
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            df.columns = ["date", "value"]
            df["date"] = pd.to_datetime(df["date"])
            
            return df
        except Exception as e:
            frappe.log_error(
                f"Error retrieving historical KPI data for {kpi_name}: {str(e)}\n{frappe.get_traceback()}",
                "KPI Data Retrieval Error"
            )
            return pd.DataFrame(columns=["date", "value"])
    
    def fill_missing_dates(self, df, start_date, end_date):
        """
        Fill in missing dates in a DataFrame with interpolated values.
        
        Args:
            df (pandas.DataFrame): DataFrame with dates and values
            start_date (str): Start date of the period (YYYY-MM-DD format)
            end_date (str): End date of the period (YYYY-MM-DD format)
            
        Returns:
            pandas.DataFrame: DataFrame with all dates in the range and interpolated values
        """
        # Create a complete date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Create a new DataFrame with the complete date range
        new_df = pd.DataFrame({"date": date_range})
        
        # Merge with the original DataFrame
        merged_df = pd.merge(new_df, df, on="date", how="left")
        
        # Interpolate missing values
        merged_df["value"] = merged_df["value"].interpolate(method="linear")
        
        return merged_df
    
    def export_kpi_data_to_csv(self, kpi_name, start_date, end_date, file_path):
        """
        Export historical KPI data to a CSV file.
        
        Args:
            kpi_name (str): Name of the KPI to export data for
            start_date (str): Start date of the period (YYYY-MM-DD format)
            end_date (str): End date of the period (YYYY-MM-DD format)
            file_path (str): Path to save the CSV file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get historical data
            df = self.get_historical_kpi_data(kpi_name, start_date, end_date)
            
            # Fill missing dates
            df = self.fill_missing_dates(df, start_date, end_date)
            
            # Export to CSV
            df.to_csv(file_path, index=False)
            
            return True
        except Exception as e:
            frappe.log_error(
                f"Error exporting KPI data to CSV: {str(e)}\n{frappe.get_traceback()}",
                "KPI Data Export Error"
            )
            return False
    
    def backfill_missing_data(self, kpi_name, start_date, end_date, filters=None):
        """
        Backfill missing historical KPI data for a period.
        
        Args:
            kpi_name (str): Name of the KPI to backfill data for
            start_date (str): Start date of the period (YYYY-MM-DD format)
            end_date (str): End date of the period (YYYY-MM-DD format)
            filters (dict, optional): Additional filters to apply to the KPI calculation
            
        Returns:
            int: Number of data points backfilled
        """
        # Get existing data
        existing_df = self.get_historical_kpi_data(kpi_name, start_date, end_date)
        
        # Create a set of existing dates
        existing_dates = set(existing_df["date"].dt.strftime("%Y-%m-%d"))
        
        # Create a list of all dates in the range
        start_date = getdate(start_date)
        end_date = getdate(end_date)
        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            all_dates.append(current_date.strftime("%Y-%m-%d"))
            current_date = add_days(current_date, 1)
        
        # Find missing dates
        missing_dates = [date for date in all_dates if date not in existing_dates]
        
        # Collect data for missing dates
        count = 0
        for date in missing_dates:
            value = self.collect_kpi_data_for_date(kpi_name, date, filters)
            if value is not None:
                count += 1
        
        return count


def create_historical_kpi_value_doctype():
    """
    Create the Historical KPI Value DocType if it doesn't exist.
    
    This function creates a new DocType to store historical KPI values
    for use in forecasting models.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if DocType already exists
        if frappe.db.exists("DocType", "Historical KPI Value"):
            return True
        
        # Create new DocType
        doctype = frappe.new_doc("DocType")
        doctype.name = "Historical KPI Value"
        doctype.module = "OnHire Pro"
        doctype.custom = 1
        doctype.autoname = "format:HKV-{kpi_name}-{date}-{company}"
        doctype.description = "Historical values of KPIs for forecasting"
        doctype.is_submittable = 0
        doctype.is_tree = 0
        doctype.is_calendar_and_gantt = 0
        
        # Add fields
        doctype.fields = [
            {
                "fieldname": "kpi_name",
                "fieldtype": "Data",
                "label": "KPI Name",
                "reqd": 1,
                "in_list_view": 1,
                "in_standard_filter": 1
            },
            {
                "fieldname": "date",
                "fieldtype": "Date",
                "label": "Date",
                "reqd": 1,
                "in_list_view": 1,
                "in_standard_filter": 1
            },
            {
                "fieldname": "actual_value",
                "fieldtype": "Float",
                "label": "Actual Value",
                "reqd": 1,
                "in_list_view": 1
            },
            {
                "fieldname": "company",
                "fieldtype": "Link",
                "label": "Company",
                "options": "Company",
                "reqd": 1,
                "in_standard_filter": 1
            },
            {
                "fieldname": "filters_json",
                "fieldtype": "Code",
                "label": "Filters JSON",
                "options": "JSON"
            }
        ]
        
        # Add permissions
        doctype.permissions = [
            {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1,
                "report": 1,
                "export": 1
            },
            {
                "role": "Analytics Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 0,
                "report": 1,
                "export": 1
            }
        ]
        
        # Save DocType
        doctype.insert()
        
        # Create indexes for better performance
        frappe.db.sql("""
            CREATE INDEX IF NOT EXISTS idx_historical_kpi_value_kpi_date
            ON `tabHistorical KPI Value` (kpi_name, date)
        """)
        
        frappe.db.sql("""
            CREATE INDEX IF NOT EXISTS idx_historical_kpi_value_company
            ON `tabHistorical KPI Value` (company)
        """)
        
        return True
    except Exception as e:
        frappe.log_error(
            f"Error creating Historical KPI Value DocType: {str(e)}\n{frappe.get_traceback()}",
            "DocType Creation Error"
        )
        return False


def collect_daily_kpi_data():
    """
    Scheduled task to collect daily KPI data for all companies.
    
    This function is intended to be run as a scheduled task at the end of each day
    to collect KPI data for all forecastable KPIs and all companies.
    
    Returns:
        dict: Summary of data collection results
    """
    try:
        # Ensure the DocType exists
        create_historical_kpi_value_doctype()
        
        # Get all active companies
        companies = frappe.get_all("Company", filters={"is_active": 1})
        
        results = {
            "total_companies": len(companies),
            "successful_companies": 0,
            "failed_companies": 0,
            "total_kpis": 0,
            "successful_kpis": 0,
            "failed_kpis": 0
        }
        
        # Current date
        today = nowdate()
        
        # Process each company
        for company_doc in companies:
            company = company_doc.name
            try:
                # Create data collector for this company
                collector = KPIDataCollector(company)
                
                # Collect data for each forecastable KPI
                for kpi_name in collector.forecastable_kpis:
                    results["total_kpis"] += 1
                    try:
                        value = collector.collect_kpi_data_for_date(kpi_name, today)
                        if value is not None:
                            results["successful_kpis"] += 1
                        else:
                            results["failed_kpis"] += 1
                    except Exception as e:
                        results["failed_kpis"] += 1
                        frappe.log_error(
                            f"Error collecting data for KPI {kpi_name} in company {company}: {str(e)}\n{frappe.get_traceback()}",
                            "Daily KPI Data Collection Error"
                        )
                
                results["successful_companies"] += 1
            except Exception as e:
                results["failed_companies"] += 1
                frappe.log_error(
                    f"Error processing company {company} for daily KPI data collection: {str(e)}\n{frappe.get_traceback()}",
                    "Daily KPI Data Collection Error"
                )
        
        # Log summary
        frappe.log_error(
            f"Daily KPI data collection completed: {json.dumps(results, indent=2)}",
            "Daily KPI Data Collection Summary"
        )
        
        return results
    except Exception as e:
        frappe.log_error(
            f"Error in daily KPI data collection: {str(e)}\n{frappe.get_traceback()}",
            "Daily KPI Data Collection Error"
        )
        return {
            "error": str(e),
            "success": False
        }


def backfill_historical_kpi_data(days=90):
    """
    Backfill historical KPI data for a specified number of days.
    
    This function collects historical KPI data for all forecastable KPIs
    and all companies for a specified number of days in the past.
    
    Args:
        days (int, optional): Number of days to backfill. Defaults to 90.
        
    Returns:
        dict: Summary of backfill results
    """
    try:
        # Ensure the DocType exists
        create_historical_kpi_value_doctype()
        
        # Get all active companies
        companies = frappe.get_all("Company", filters={"is_active": 1})
        
        results = {
            "total_companies": len(companies),
            "successful_companies": 0,
            "failed_companies": 0,
            "total_kpis": 0,
            "successful_kpis": 0,
            "failed_kpis": 0,
            "total_datapoints": 0,
            "backfilled_datapoints": 0
        }
        
        # Calculate date range
        end_date = add_days(nowdate(), -1)  # Yesterday
        start_date = add_days(end_date, -days)  # X days before yesterday
        
        # Process each company
        for company_doc in companies:
            company = company_doc.name
            try:
                # Create data collector for this company
                collector = KPIDataCollector(company)
                
                # Backfill data for each forecastable KPI
                for kpi_name in collector.forecastable_kpis:
                    results["total_kpis"] += 1
                    try:
                        # Calculate total datapoints for this KPI
                        total_days = days + 1  # Include both start and end dates
                        results["total_datapoints"] += total_days
                        
                        # Backfill missing data
                        backfilled = collector.backfill_missing_data(kpi_name, start_date, end_date)
                        results["backfilled_datapoints"] += backfilled
                        
                        results["successful_kpis"] += 1
                    except Exception as e:
                        results["failed_kpis"] += 1
                        frappe.log_error(
                            f"Error backfilling data for KPI {kpi_name} in company {company}: {str(e)}\n{frappe.get_traceback()}",
                            "Historical KPI Data Backfill Error"
                        )
                
                results["successful_companies"] += 1
            except Exception as e:
                results["failed_companies"] += 1
                frappe.log_error(
                    f"Error processing company {company} for historical KPI data backfill: {str(e)}\n{frappe.get_traceback()}",
                    "Historical KPI Data Backfill Error"
                )
        
        # Log summary
        frappe.log_error(
            f"Historical KPI data backfill completed: {json.dumps(results, indent=2)}",
            "Historical KPI Data Backfill Summary"
        )
        
        return results
    except Exception as e:
        frappe.log_error(
            f"Error in historical KPI data backfill: {str(e)}\n{frappe.get_traceback()}",
            "Historical KPI Data Backfill Error"
        )
        return {
            "error": str(e),
            "success": False
        }


# Command-line interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="KPI Data Collection Tool")
    parser.add_argument("--company", help="Company to collect data for")
    parser.add_argument("--kpi", help="KPI to collect data for")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--export", help="Export data to CSV file")
    parser.add_argument("--backfill", type=int, help="Backfill data for specified number of days")
    parser.add_argument("--daily", action="store_true", help="Run daily data collection")
    
    args = parser.parse_args()
    
    if args.daily:
        print("Running daily KPI data collection...")
        results = collect_daily_kpi_data()
        print(json.dumps(results, indent=2))
    elif args.backfill:
        print(f"Backfilling KPI data for {args.backfill} days...")
        results = backfill_historical_kpi_data(args.backfill)
        print(json.dumps(results, indent=2))
    elif args.kpi and args.start_date and args.end_date:
        collector = KPIDataCollector(args.company)
        if args.export:
            print(f"Exporting KPI data to {args.export}...")
            success = collector.export_kpi_data_to_csv(args.kpi, args.start_date, args.end_date, args.export)
            print(f"Export {'successful' if success else 'failed'}")
        else:
            print(f"Collecting data for KPI {args.kpi} from {args.start_date} to {args.end_date}...")
            df = collector.collect_kpi_data_for_period(args.kpi, args.start_date, args.end_date)
            print(df)
    else:
        parser.print_help()
