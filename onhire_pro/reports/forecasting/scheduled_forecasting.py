import frappe
import json
import os
from datetime import datetime, timedelta
from frappe.utils import nowdate, add_days, getdate, add_months, get_datetime
from onhire_pro.reports.forecasting.data_collector import collect_daily_kpi_data, backfill_historical_kpi_data
from onhire_pro.reports.forecasting.forecasting_engine import generate_weekly_forecasts

def schedule_forecasting_tasks():
    """
    Set up scheduled tasks for KPI data collection and forecasting.
    
    This function creates scheduled tasks in ERPNext for:
    1. Daily KPI data collection (runs at end of day)
    2. Weekly forecast generation (runs on weekends)
    3. Monthly forecast accuracy evaluation (runs at month end)
    
    Returns:
        dict: Status of scheduled task creation
    """
    try:
        # Check if scheduled tasks already exist
        existing_tasks = frappe.get_all(
            "Scheduled Job Type",
            filters={"method": ["in", [
                "onhire_pro.reports.forecasting.scheduled_forecasting.run_daily_kpi_collection",
                "onhire_pro.reports.forecasting.scheduled_forecasting.run_weekly_forecasting",
                "onhire_pro.reports.forecasting.scheduled_forecasting.run_monthly_forecast_evaluation"
            ]]},
            fields=["name", "method"]
        )
        
        existing_methods = [task.method for task in existing_tasks]
        
        results = {
            "daily_collection": False,
            "weekly_forecasting": False,
            "monthly_evaluation": False
        }
        
        # Create daily KPI collection task if it doesn't exist
        if "onhire_pro.reports.forecasting.scheduled_forecasting.run_daily_kpi_collection" not in existing_methods:
            daily_task = frappe.new_doc("Scheduled Job Type")
            daily_task.update({
                "method": "onhire_pro.reports.forecasting.scheduled_forecasting.run_daily_kpi_collection",
                "frequency": "Daily",
                "cron_format": "0 23 * * *",  # Run at 11:00 PM every day
                "priority": 5,
                "server_script_method": False,
                "documentation": "Collects daily KPI data for all companies for use in forecasting"
            })
            daily_task.save()
            results["daily_collection"] = True
        else:
            results["daily_collection"] = "Already exists"
        
        # Create weekly forecasting task if it doesn't exist
        if "onhire_pro.reports.forecasting.scheduled_forecasting.run_weekly_forecasting" not in existing_methods:
            weekly_task = frappe.new_doc("Scheduled Job Type")
            weekly_task.update({
                "method": "onhire_pro.reports.forecasting.scheduled_forecasting.run_weekly_forecasting",
                "frequency": "Weekly",
                "cron_format": "0 2 * * 0",  # Run at 2:00 AM every Sunday
                "priority": 3,
                "server_script_method": False,
                "documentation": "Generates weekly forecasts for all KPIs and companies"
            })
            weekly_task.save()
            results["weekly_forecasting"] = True
        else:
            results["weekly_forecasting"] = "Already exists"
        
        # Create monthly forecast evaluation task if it doesn't exist
        if "onhire_pro.reports.forecasting.scheduled_forecasting.run_monthly_forecast_evaluation" not in existing_methods:
            monthly_task = frappe.new_doc("Scheduled Job Type")
            monthly_task.update({
                "method": "onhire_pro.reports.forecasting.scheduled_forecasting.run_monthly_forecast_evaluation",
                "frequency": "Monthly",
                "cron_format": "0 3 1 * *",  # Run at 3:00 AM on the 1st day of each month
                "priority": 4,
                "server_script_method": False,
                "documentation": "Evaluates forecast accuracy by comparing forecasts with actual values"
            })
            monthly_task.save()
            results["monthly_evaluation"] = True
        else:
            results["monthly_evaluation"] = "Already exists"
        
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        frappe.log_error(
            f"Error setting up scheduled forecasting tasks: {str(e)}\n{frappe.get_traceback()}",
            "Scheduled Task Setup Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


def run_daily_kpi_collection():
    """
    Scheduled task to collect daily KPI data.
    
    This function is called by the scheduler at the end of each day
    to collect KPI data for all forecastable KPIs and all companies.
    
    Returns:
        dict: Results of the data collection
    """
    try:
        frappe.logger().info("Starting daily KPI data collection")
        results = collect_daily_kpi_data()
        frappe.logger().info(f"Daily KPI data collection completed: {json.dumps(results, indent=2)}")
        return results
    except Exception as e:
        error_msg = f"Error in daily KPI data collection: {str(e)}"
        frappe.logger().error(error_msg)
        frappe.log_error(
            f"{error_msg}\n{frappe.get_traceback()}",
            "Daily KPI Collection Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


def run_weekly_forecasting():
    """
    Scheduled task to generate weekly forecasts.
    
    This function is called by the scheduler on weekends
    to generate forecasts for all forecastable KPIs and all companies.
    
    Returns:
        dict: Results of the forecasting
    """
    try:
        frappe.logger().info("Starting weekly KPI forecasting")
        results = generate_weekly_forecasts()
        frappe.logger().info(f"Weekly KPI forecasting completed: {json.dumps(results, indent=2)}")
        return results
    except Exception as e:
        error_msg = f"Error in weekly KPI forecasting: {str(e)}"
        frappe.logger().error(error_msg)
        frappe.log_error(
            f"{error_msg}\n{frappe.get_traceback()}",
            "Weekly Forecasting Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


def run_monthly_forecast_evaluation():
    """
    Scheduled task to evaluate forecast accuracy.
    
    This function is called by the scheduler at the beginning of each month
    to evaluate the accuracy of forecasts by comparing them with actual values.
    
    Returns:
        dict: Results of the evaluation
    """
    try:
        frappe.logger().info("Starting monthly forecast evaluation")
        
        # Get all active companies
        companies = frappe.get_all("Company", filters={"is_active": 1})
        
        results = {
            "total_companies": len(companies),
            "successful_companies": 0,
            "failed_companies": 0,
            "total_kpis": 0,
            "successful_kpis": 0,
            "failed_kpis": 0,
            "evaluations": {}
        }
        
        # Calculate date range for evaluation
        # We evaluate forecasts made one month ago
        today = getdate(nowdate())
        first_day_last_month = getdate(f"{today.year}-{today.month-1 if today.month > 1 else 12}-01")
        if today.month == 1:
            first_day_last_month = getdate(f"{today.year-1}-12-01")
        
        last_day_last_month = add_days(getdate(f"{today.year}-{today.month}-01"), -1)
        
        # Get forecasts made on the first day of last month
        forecast_date = first_day_last_month.strftime("%Y-%m-%d")
        
        # Import here to avoid circular imports
        from onhire_pro.reports.forecasting.forecasting_engine import ForecastingEngine
        from onhire_pro.reports.forecasting.data_collector import KPIDataCollector
        
        # Process each company
        for company_doc in companies:
            company = company_doc.name
            try:
                # Create forecasting engine for this company
                engine = ForecastingEngine(company)
                collector = KPIDataCollector(company)
                
                # Evaluate forecasts for each forecastable KPI
                for kpi_name in collector.forecastable_kpis:
                    results["total_kpis"] += 1
                    try:
                        # Compare forecast with actual values
                        comparison = engine.compare_forecast_with_actual(
                            kpi_name,
                            forecast_date,
                            start_date=forecast_date,
                            end_date=last_day_last_month.strftime("%Y-%m-%d")
                        )
                        
                        if comparison["success"]:
                            results["successful_kpis"] += 1
                            
                            # Store evaluation results
                            if company not in results["evaluations"]:
                                results["evaluations"][company] = {}
                            
                            results["evaluations"][company][kpi_name] = {
                                "metrics": comparison["metrics"],
                                "data_points": comparison["data_points"]
                            }
                        else:
                            results["failed_kpis"] += 1
                            frappe.log_error(
                                f"Error evaluating forecast for KPI {kpi_name} in company {company}: {comparison.get('error', 'Unknown error')}",
                                "Forecast Evaluation Error"
                            )
                    except Exception as e:
                        results["failed_kpis"] += 1
                        frappe.log_error(
                            f"Error evaluating forecast for KPI {kpi_name} in company {company}: {str(e)}\n{frappe.get_traceback()}",
                            "Forecast Evaluation Error"
                        )
                
                results["successful_companies"] += 1
            except Exception as e:
                results["failed_companies"] += 1
                frappe.log_error(
                    f"Error processing company {company} for forecast evaluation: {str(e)}\n{frappe.get_traceback()}",
                    "Forecast Evaluation Error"
                )
        
        # Log summary
        frappe.log_error(
            f"Monthly forecast evaluation completed: {json.dumps(results, indent=2)}",
            "Forecast Evaluation Summary"
        )
        
        frappe.logger().info(f"Monthly forecast evaluation completed")
        return results
    except Exception as e:
        error_msg = f"Error in monthly forecast evaluation: {str(e)}"
        frappe.logger().error(error_msg)
        frappe.log_error(
            f"{error_msg}\n{frappe.get_traceback()}",
            "Monthly Forecast Evaluation Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


def backfill_data_for_initial_setup(days=90):
    """
    Backfill historical KPI data for initial setup.
    
    This function should be run once during initial setup to collect
    historical KPI data for use in forecasting.
    
    Args:
        days (int, optional): Number of days to backfill. Defaults to 90.
        
    Returns:
        dict: Results of the backfill operation
    """
    try:
        frappe.logger().info(f"Starting historical data backfill for {days} days")
        results = backfill_historical_kpi_data(days)
        frappe.logger().info(f"Historical data backfill completed: {json.dumps(results, indent=2)}")
        return results
    except Exception as e:
        error_msg = f"Error in historical data backfill: {str(e)}"
        frappe.logger().error(error_msg)
        frappe.log_error(
            f"{error_msg}\n{frappe.get_traceback()}",
            "Historical Data Backfill Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


# Command-line interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scheduled Forecasting Tasks")
    parser.add_argument("--setup", action="store_true", help="Set up scheduled tasks")
    parser.add_argument("--daily", action="store_true", help="Run daily KPI data collection")
    parser.add_argument("--weekly", action="store_true", help="Run weekly forecasting")
    parser.add_argument("--monthly", action="store_true", help="Run monthly forecast evaluation")
    parser.add_argument("--backfill", type=int, help="Backfill historical data for specified number of days")
    
    args = parser.parse_args()
    
    if args.setup:
        print("Setting up scheduled forecasting tasks...")
        results = schedule_forecasting_tasks()
        print(json.dumps(results, indent=2))
    elif args.daily:
        print("Running daily KPI data collection...")
        results = run_daily_kpi_collection()
        print(json.dumps(results, indent=2))
    elif args.weekly:
        print("Running weekly forecasting...")
        results = run_weekly_forecasting()
        print(json.dumps(results, indent=2))
    elif args.monthly:
        print("Running monthly forecast evaluation...")
        results = run_monthly_forecast_evaluation()
        print(json.dumps(results, indent=2))
    elif args.backfill:
        print(f"Backfilling historical data for {args.backfill} days...")
        results = backfill_data_for_initial_setup(args.backfill)
        print(json.dumps(results, indent=2))
    else:
        parser.print_help()
