"""
OnHire Pro - Rental Management Application for ERPNext

This module contains the KPI utility functions for the OnHire Pro application.
These functions are used by dashboard charts and reports to calculate various
key performance indicators (KPIs) for rental operations.

Each function follows a consistent pattern:
- Takes a filters dictionary as input
- Performs necessary database queries
- Calculates the KPI value
- Returns the result in the format expected by the dashboard chart

Error handling is implemented throughout to ensure robustness in production.
"""

import frappe
from frappe.utils import getdate, nowdate, add_days, date_diff, flt, cint
from datetime import datetime, timedelta
import json
import calendar

def calculate_item_utilization_rate(filters):
    """
    Calculate the utilization rate of rental items.
    
    The utilization rate is calculated as the ratio of total rental days to total available days,
    expressed as a percentage. This KPI indicates how effectively the rental inventory is being used.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the calculated utilization rate:
            - value (float): Utilization rate as a percentage
            
    Example:
        >>> calculate_item_utilization_rate({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {'value': 75.5}
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for item utilization rate calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get total rental days for the period
        total_rental_days = frappe.db.sql("""
            SELECT SUM(DATEDIFF(
                LEAST(rji.end_date, %s),
                GREATEST(rji.start_date, %s)
            ) + 1) as total_days
            FROM `tabRental Job Item` rji
            JOIN `tabRental Job` rj ON rji.parent = rj.name
            WHERE rj.company = %s
            AND rji.start_date <= %s
            AND rji.end_date >= %s
            AND rj.docstatus = 1
        """, (filters.get("to_date"), filters.get("from_date"), filters.get("company"), 
              filters.get("to_date"), filters.get("from_date")))
        
        total_rental_days = flt(total_rental_days[0][0]) if total_rental_days and total_rental_days[0][0] else 0
        
        # Get all rental items
        rental_items = frappe.db.get_all(
            "Item",
            filters={
                "is_rental_item": 1,
                "company": filters.get("company")
            },
            fields=["name", "creation"]
        )
        
        if not rental_items:
            return {"value": 0}
        
        # Calculate total available days
        total_available_days = 0
        to_date = getdate(filters.get("to_date"))
        from_date = getdate(filters.get("from_date"))
        
        for item in rental_items:
            item_creation = getdate(item.creation)
            
            # If item was created after the from_date, use creation date as start
            start_date = max(from_date, item_creation)
            
            # Calculate available days for this item
            available_days = date_diff(to_date, start_date) + 1
            total_available_days += available_days
        
        # Calculate utilization rate
        utilization_rate = (total_rental_days / total_available_days * 100) if total_available_days > 0 else 0
        
        return {"value": utilization_rate}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating item utilization rate: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def calculate_average_rental_duration(filters):
    """
    Calculate the average duration of rental jobs.
    
    The average rental duration is calculated as the average number of days between
    the start and end dates of completed rental jobs. This KPI helps understand
    typical rental periods and can inform pricing and availability planning.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the calculated average duration:
            - value (float): Average rental duration in days
            
    Example:
        >>> calculate_average_rental_duration({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {'value': 7.5}
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for average rental duration calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get rental durations for completed jobs
        rental_durations = frappe.db.sql("""
            SELECT DATEDIFF(end_date, start_date) + 1 as rental_duration
            FROM `tabRental Job`
            WHERE company = %s
            AND status = 'Completed'
            AND end_date BETWEEN %s AND %s
            AND docstatus = 1
        """, (filters.get("company"), filters.get("from_date"), filters.get("to_date")), as_dict=1)
        
        if not rental_durations:
            return {"value": 0}
        
        # Calculate average duration
        total_duration = sum(job.rental_duration for job in rental_durations)
        average_duration = total_duration / len(rental_durations)
        
        return {"value": average_duration}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating average rental duration: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_revenue_per_item_category(filters):
    """
    Calculate the revenue distribution across different item categories.
    
    This function returns the revenue generated by each item category during the specified period.
    The data is formatted for display in a pie or bar chart, showing the contribution of each
    category to the overall rental revenue.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the revenue distribution data:
            - labels (list): List of item category names
            - datasets (list): List containing a single dataset with:
                - name (str): Dataset name
                - values (list): Revenue values corresponding to each category
                
    Example:
        >>> get_revenue_per_item_category({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {
            'labels': ['Heavy Equipment', 'Tools', 'Vehicles'],
            'datasets': [{'name': 'Revenue', 'values': [5000, 3000, 2000]}]
        }
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for revenue per item category calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Revenue", "values": []}]}
        
        # Get revenue by item category
        revenue_data = frappe.db.sql("""
            SELECT i.item_group, SUM(rji.amount) as total_revenue
            FROM `tabRental Job Item` rji
            JOIN `tabRental Job` rj ON rji.parent = rj.name
            JOIN `tabItem` i ON rji.item_code = i.name
            WHERE rj.company = %s
            AND rj.start_date <= %s
            AND rj.end_date >= %s
            AND rj.docstatus = 1
            GROUP BY i.item_group
            ORDER BY total_revenue DESC
        """, (filters.get("company"), filters.get("to_date"), filters.get("from_date")), as_dict=1)
        
        if not revenue_data:
            return {"labels": [], "datasets": [{"name": "Revenue", "values": []}]}
        
        # Format data for chart
        labels = [d.item_group for d in revenue_data]
        values = [d.total_revenue for d in revenue_data]
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "name": "Revenue",
                    "values": values
                }
            ]
        }
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating revenue per item category: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"labels": [], "datasets": [{"name": "Revenue", "values": []}]}

def calculate_avg_maintenance_turnaround_time(filters):
    """
    Calculate the average turnaround time for maintenance tasks.
    
    The average maintenance turnaround time is calculated as the average number of days
    between the creation and completion of maintenance tasks. This KPI helps monitor
    maintenance efficiency and identify potential bottlenecks.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the calculated average turnaround time:
            - value (float): Average turnaround time in days
            
    Example:
        >>> calculate_avg_maintenance_turnaround_time({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {'value': 3.2}
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for maintenance turnaround time calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Maintenance Task"):
            frappe.log_error(
                "Maintenance Task doctype does not exist",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get turnaround times for completed maintenance tasks
        turnaround_times = frappe.db.sql("""
            SELECT DATEDIFF(completion_date, creation) as turnaround_time
            FROM `tabMaintenance Task`
            WHERE company = %s
            AND status = 'Completed'
            AND completion_date BETWEEN %s AND %s
            AND docstatus = 1
        """, (filters.get("company"), filters.get("from_date"), filters.get("to_date")), as_dict=1)
        
        if not turnaround_times:
            return {"value": 0}
        
        # Calculate average turnaround time
        total_time = sum(task.turnaround_time for task in turnaround_times)
        average_time = total_time / len(turnaround_times)
        
        return {"value": average_time}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating maintenance turnaround time: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def calculate_booking_conversion_rate(filters):
    """
    Calculate the conversion rate from quotations to confirmed rental jobs.
    
    The booking conversion rate is calculated as the percentage of quotations that
    are converted to confirmed rental jobs. This KPI helps measure sales effectiveness
    and identify potential issues in the quotation-to-booking process.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the calculated conversion rate:
            - value (float): Conversion rate as a percentage
            
    Example:
        >>> calculate_booking_conversion_rate({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {'value': 65.0}
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for booking conversion rate calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Quotation") or not frappe.db.exists("DocType", "Rental Job"):
            frappe.log_error(
                "Required doctypes do not exist for booking conversion rate calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Count total rental quotations
        total_quotations = frappe.db.count("Quotation", {
            "company": filters.get("company"),
            "transaction_date": ["between", [filters.get("from_date"), filters.get("to_date")]],
            "docstatus": 1,
            "rental_quotation": 1
        })
        
        if total_quotations == 0:
            return {"value": 0}
        
        # Count converted quotations
        converted_quotations = frappe.db.count("Rental Job", {
            "company": filters.get("company"),
            "creation": ["between", [filters.get("from_date"), filters.get("to_date")]],
            "docstatus": 1,
            "quotation": ["!=", ""]
        })
        
        # Calculate conversion rate
        conversion_rate = (converted_quotations / total_quotations) * 100
        
        return {"value": conversion_rate}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating booking conversion rate: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def calculate_customer_churn_rate(filters):
    """
    Calculate the customer churn rate for rental customers.
    
    The customer churn rate is calculated as the percentage of customers who did not
    rent again within the specified period after their last rental. This KPI helps
    measure customer retention and identify potential issues in customer satisfaction.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the calculated churn rate:
            - value (float): Churn rate as a percentage
            
    Example:
        >>> calculate_customer_churn_rate({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {'value': 15.0}
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for customer churn rate calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get customers at the start of the period
        customers_at_start = frappe.db.sql("""
            SELECT COUNT(DISTINCT customer) as count
            FROM `tabRental Job`
            WHERE company = %s
            AND creation < %s
            AND docstatus = 1
        """, (filters.get("company"), filters.get("from_date")))
        
        customers_at_start = cint(customers_at_start[0][0]) if customers_at_start and customers_at_start[0][0] else 0
        
        if customers_at_start == 0:
            return {"value": 0}
        
        # Get customers at the end of the period
        customers_at_end = frappe.db.sql("""
            SELECT COUNT(DISTINCT customer) as count
            FROM `tabRental Job`
            WHERE company = %s
            AND creation <= %s
            AND docstatus = 1
        """, (filters.get("company"), filters.get("to_date")))
        
        customers_at_end = cint(customers_at_end[0][0]) if customers_at_end and customers_at_end[0][0] else 0
        
        # Get new customers during the period
        new_customers = frappe.db.sql("""
            SELECT COUNT(DISTINCT customer) as count
            FROM `tabRental Job`
            WHERE company = %s
            AND creation BETWEEN %s AND %s
            AND customer NOT IN (
                SELECT DISTINCT customer
                FROM `tabRental Job`
                WHERE company = %s
                AND creation < %s
                AND docstatus = 1
            )
            AND docstatus = 1
        """, (filters.get("company"), filters.get("from_date"), filters.get("to_date"), 
              filters.get("company"), filters.get("from_date")))
        
        new_customers = cint(new_customers[0][0]) if new_customers and new_customers[0][0] else 0
        
        # Calculate churn rate
        # Customers lost = (Start + New) - End
        customers_lost = (customers_at_start + new_customers) - customers_at_end
        
        # Churn rate = (Customers lost / Start) * 100
        churn_rate = (customers_lost / customers_at_start) * 100 if customers_at_start > 0 else 0
        
        return {"value": churn_rate}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating customer churn rate: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def calculate_damage_rate(filters):
    """
    Calculate the damage rate for rental items.
    
    The damage rate is calculated as the percentage of rental jobs where items were
    returned with damage. This KPI helps monitor the condition of rental inventory
    and identify potential issues with specific items or customers.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the calculated damage rate:
            - value (float): Damage rate as a percentage
            
    Example:
        >>> calculate_damage_rate({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {'value': 8.5}
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for damage rate calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job") or not frappe.db.exists("DocType", "Condition Assessment"):
            frappe.log_error(
                "Required doctypes do not exist for damage rate calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Count total completed rentals
        total_rentals = frappe.db.count("Rental Job", {
            "company": filters.get("company"),
            "end_date": ["between", [filters.get("from_date"), filters.get("to_date")]],
            "status": "Completed",
            "docstatus": 1
        })
        
        if total_rentals == 0:
            return {"value": 0}
        
        # Count rentals with damaged items
        damaged_rentals = frappe.db.count("Rental Job", {
            "company": filters.get("company"),
            "end_date": ["between", [filters.get("from_date"), filters.get("to_date")]],
            "status": "Completed",
            "docstatus": 1,
            "has_damaged_items": 1
        })
        
        # Calculate damage rate
        damage_rate = (damaged_rentals / total_rentals) * 100
        
        return {"value": damage_rate}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating damage rate: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_stock_reservation_conflicts(filters):
    """
    Calculate the number of stock reservation conflicts.
    
    Stock reservation conflicts occur when the same item is reserved for multiple
    rental jobs that overlap in time. This KPI helps identify potential overbooking
    issues and prevent customer disappointment.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the calculated number of conflicts:
            - value (int): Number of stock reservation conflicts
            
    Example:
        >>> get_stock_reservation_conflicts({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {'value': 3}
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for stock reservation conflicts calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job") or not frappe.db.exists("DocType", "Rental Job Item"):
            frappe.log_error(
                "Required doctypes do not exist for stock reservation conflicts calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get stock reservation conflicts
        conflicts = frappe.db.sql("""
            SELECT rji1.item_code, rji1.warehouse, COUNT(*) as conflicts
            FROM `tabRental Job Item` rji1
            JOIN `tabRental Job` rj1 ON rji1.parent = rj1.name
            JOIN `tabRental Job Item` rji2 ON rji1.item_code = rji2.item_code AND rji1.warehouse = rji2.warehouse
            JOIN `tabRental Job` rj2 ON rji2.parent = rj2.name
            WHERE rj1.company = %s
            AND rj1.docstatus = 1
            AND rj2.docstatus = 1
            AND rj1.name != rj2.name
            AND rj1.start_date <= %s
            AND rj1.end_date >= %s
            AND rj2.start_date <= %s
            AND rj2.end_date >= %s
            AND (
                (rji1.start_date <= rji2.end_date AND rji1.end_date >= rji2.start_date)
            )
            GROUP BY rji1.item_code, rji1.warehouse
        """, (filters.get("company"), filters.get("to_date"), filters.get("from_date"),
              filters.get("to_date"), filters.get("from_date")), as_dict=1)
        
        # Calculate total conflicts
        total_conflicts = sum(conflict.conflicts for conflict in conflicts) if conflicts else 0
        
        return {"value": total_conflicts}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating stock reservation conflicts: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_overdue_returns_count(filters):
    """
    Calculate the number of overdue rental returns.
    
    Overdue returns are rental jobs where the end date has passed but the items
    have not been returned. This KPI helps identify potential revenue leakage and
    inventory management issues.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - as_of_date (str, optional): Date to check overdue status (defaults to today)
            
    Returns:
        dict: Dictionary containing the calculated number of overdue returns:
            - value (int): Number of overdue returns
            
    Example:
        >>> get_overdue_returns_count({"company": "Example Inc."})
        {'value': 5}
    """
    try:
        # Validate required filters
        if not filters.get("company"):
            frappe.log_error(
                f"Missing required filters for overdue returns count calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job"):
            frappe.log_error(
                "Required doctypes do not exist for overdue returns count calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get as_of_date from filters or use today
        as_of_date = filters.get("as_of_date") or nowdate()
        
        # Count overdue returns
        overdue_count = frappe.db.count("Rental Job", {
            "company": filters.get("company"),
            "end_date": ["<", as_of_date],
            "status": ["in", ["In Progress", "Confirmed"]],
            "docstatus": 1
        })
        
        return {"value": overdue_count}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating overdue returns count: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_active_rental_jobs_count(filters):
    """
    Calculate the number of active rental jobs.
    
    Active rental jobs are those with status 'Confirmed' or 'In Progress'. This KPI
    helps monitor the current workload and operational activity.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - as_of_date (str, optional): Date to check active status (defaults to today)
            
    Returns:
        dict: Dictionary containing the calculated number of active rental jobs:
            - value (int): Number of active rental jobs
            
    Example:
        >>> get_active_rental_jobs_count({"company": "Example Inc."})
        {'value': 12}
    """
    try:
        # Validate required filters
        if not filters.get("company"):
            frappe.log_error(
                f"Missing required filters for active rental jobs count calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job"):
            frappe.log_error(
                "Required doctypes do not exist for active rental jobs count calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get as_of_date from filters or use today
        as_of_date = filters.get("as_of_date") or nowdate()
        
        # Count active rental jobs
        active_count = frappe.db.count("Rental Job", {
            "company": filters.get("company"),
            "start_date": ["<=", as_of_date],
            "end_date": [">=", as_of_date],
            "status": ["in", ["Confirmed", "In Progress"]],
            "docstatus": 1
        })
        
        return {"value": active_count}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating active rental jobs count: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_jobs_due_for_dispatch_count(filters):
    """
    Calculate the number of rental jobs due for dispatch.
    
    Jobs due for dispatch are those with status 'Confirmed' and a start date within
    the specified time frame. This KPI helps plan logistics and resource allocation.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str, optional): Start date for due period (defaults to today)
            - to_date (str, optional): End date for due period (defaults to 7 days from today)
            
    Returns:
        dict: Dictionary containing the calculated number of jobs due for dispatch:
            - value (int): Number of jobs due for dispatch
            
    Example:
        >>> get_jobs_due_for_dispatch_count({"company": "Example Inc."})
        {'value': 8}
    """
    try:
        # Validate required filters
        if not filters.get("company"):
            frappe.log_error(
                f"Missing required filters for jobs due for dispatch count calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job"):
            frappe.log_error(
                "Required doctypes do not exist for jobs due for dispatch count calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get date range from filters or use defaults
        from_date = filters.get("from_date") or nowdate()
        to_date = filters.get("to_date") or add_days(nowdate(), 7)
        
        # Count jobs due for dispatch
        dispatch_count = frappe.db.count("Rental Job", {
            "company": filters.get("company"),
            "start_date": ["between", [from_date, to_date]],
            "status": "Confirmed",
            "docstatus": 1
        })
        
        return {"value": dispatch_count}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating jobs due for dispatch count: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_jobs_due_for_return_count(filters):
    """
    Calculate the number of rental jobs due for return.
    
    Jobs due for return are those with status 'In Progress' and an end date within
    the specified time frame. This KPI helps plan logistics and resource allocation.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str, optional): Start date for due period (defaults to today)
            - to_date (str, optional): End date for due period (defaults to 7 days from today)
            
    Returns:
        dict: Dictionary containing the calculated number of jobs due for return:
            - value (int): Number of jobs due for return
            
    Example:
        >>> get_jobs_due_for_return_count({"company": "Example Inc."})
        {'value': 6}
    """
    try:
        # Validate required filters
        if not filters.get("company"):
            frappe.log_error(
                f"Missing required filters for jobs due for return count calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job"):
            frappe.log_error(
                "Required doctypes do not exist for jobs due for return count calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get date range from filters or use defaults
        from_date = filters.get("from_date") or nowdate()
        to_date = filters.get("to_date") or add_days(nowdate(), 7)
        
        # Count jobs due for return
        return_count = frappe.db.count("Rental Job", {
            "company": filters.get("company"),
            "end_date": ["between", [from_date, to_date]],
            "status": "In Progress",
            "docstatus": 1
        })
        
        return {"value": return_count}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating jobs due for return count: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_at_risk_stock_count(filters):
    """
    Calculate the number of items where reservations exceed available stock.
    
    At-risk stock items are those where the number of items reserved for rental jobs
    exceeds the actual available quantity. This KPI helps identify potential inventory
    shortages and prevent overbooking.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - as_of_date (str, optional): Date to check stock status (defaults to today)
            
    Returns:
        dict: Dictionary containing the calculated number of at-risk stock items:
            - value (int): Number of at-risk stock items
            
    Example:
        >>> get_at_risk_stock_count({"company": "Example Inc."})
        {'value': 3}
    """
    try:
        # Validate required filters
        if not filters.get("company"):
            frappe.log_error(
                f"Missing required filters for at-risk stock count calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job") or not frappe.db.exists("DocType", "Bin"):
            frappe.log_error(
                "Required doctypes do not exist for at-risk stock count calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get as_of_date from filters or use today
        as_of_date = filters.get("as_of_date") or nowdate()
        
        # Get at-risk stock items
        at_risk_items = frappe.db.sql("""
            SELECT rji.item_code, rji.warehouse, 
                   SUM(rji.qty) as reserved_qty,
                   b.actual_qty
            FROM `tabRental Job Item` rji
            JOIN `tabRental Job` rj ON rji.parent = rj.name
            JOIN `tabBin` b ON rji.item_code = b.item_code AND rji.warehouse = b.warehouse
            WHERE rj.company = %s
            AND rj.docstatus = 1
            AND rj.status IN ('Confirmed', 'In Progress')
            AND rji.start_date <= %s
            AND rji.end_date >= %s
            GROUP BY rji.item_code, rji.warehouse
            HAVING reserved_qty > actual_qty
        """, (filters.get("company"), as_of_date, as_of_date), as_dict=1)
        
        # Count at-risk items
        at_risk_count = len(at_risk_items)
        
        return {"value": at_risk_count}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating at-risk stock count: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_items_awaiting_assessment_count(filters):
    """
    Calculate the number of items awaiting condition assessment.
    
    Items awaiting assessment are those that have been returned from rental jobs
    but have not yet undergone a condition assessment. This KPI helps monitor the
    efficiency of the post-rental process.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - as_of_date (str, optional): Date to check assessment status (defaults to today)
            
    Returns:
        dict: Dictionary containing the calculated number of items awaiting assessment:
            - value (int): Number of items awaiting assessment
            
    Example:
        >>> get_items_awaiting_assessment_count({"company": "Example Inc."})
        {'value': 7}
    """
    try:
        # Validate required filters
        if not filters.get("company"):
            frappe.log_error(
                f"Missing required filters for items awaiting assessment count calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Condition Assessment"):
            frappe.log_error(
                "Required doctypes do not exist for items awaiting assessment count calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get as_of_date from filters or use today
        as_of_date = filters.get("as_of_date") or nowdate()
        
        # Count items awaiting assessment
        assessment_count = frappe.db.count("Condition Assessment", {
            "company": filters.get("company"),
            "status": "Pending Post-Rental",
            "creation": ["<=", as_of_date],
            "docstatus": 1
        })
        
        return {"value": assessment_count}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating items awaiting assessment count: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_items_in_maintenance_count(filters):
    """
    Calculate the number of items currently in maintenance.
    
    Items in maintenance are those that have an active maintenance task with status
    other than 'Completed'. This KPI helps monitor the maintenance workload and
    potential impact on rental availability.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - as_of_date (str, optional): Date to check maintenance status (defaults to today)
            
    Returns:
        dict: Dictionary containing the calculated number of items in maintenance:
            - value (int): Number of items in maintenance
            
    Example:
        >>> get_items_in_maintenance_count({"company": "Example Inc."})
        {'value': 4}
    """
    try:
        # Validate required filters
        if not filters.get("company"):
            frappe.log_error(
                f"Missing required filters for items in maintenance count calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Maintenance Task"):
            frappe.log_error(
                "Required doctypes do not exist for items in maintenance count calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get as_of_date from filters or use today
        as_of_date = filters.get("as_of_date") or nowdate()
        
        # Count items in maintenance
        maintenance_count = frappe.db.count("Maintenance Task", {
            "company": filters.get("company"),
            "status": ["!=", "Completed"],
            "start_date": ["<=", as_of_date],
            "docstatus": 1
        })
        
        return {"value": maintenance_count}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating items in maintenance count: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_total_rental_revenue(filters):
    """
    Calculate the total rental revenue for the specified period.
    
    Total rental revenue is the sum of all invoiced amounts for rental jobs during
    the specified period. This KPI is a key financial metric for rental operations.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the calculated total revenue:
            - value (float): Total rental revenue
            
    Example:
        >>> get_total_rental_revenue({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {'value': 25000.0}
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for total rental revenue calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Sales Invoice") or not frappe.db.exists("DocType", "Rental Job"):
            frappe.log_error(
                "Required doctypes do not exist for total rental revenue calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get total rental revenue
        total_revenue = frappe.db.sql("""
            SELECT SUM(si.grand_total) as total_revenue
            FROM `tabSales Invoice` si
            WHERE si.company = %s
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
            AND si.rental_job IS NOT NULL
        """, (filters.get("company"), filters.get("from_date"), filters.get("to_date")))
        
        total_revenue = flt(total_revenue[0][0]) if total_revenue and total_revenue[0][0] else 0
        
        return {"value": total_revenue}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating total rental revenue: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_open_rental_quotation_value(filters):
    """
    Calculate the total value of open rental quotations.
    
    Open rental quotation value is the sum of all quotation amounts for rental jobs
    that have not yet been converted to rental jobs. This KPI helps forecast potential
    future revenue.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - as_of_date (str, optional): Date to check quotation status (defaults to today)
            
    Returns:
        dict: Dictionary containing the calculated open quotation value:
            - value (float): Total value of open rental quotations
            
    Example:
        >>> get_open_rental_quotation_value({"company": "Example Inc."})
        {'value': 15000.0}
    """
    try:
        # Validate required filters
        if not filters.get("company"):
            frappe.log_error(
                f"Missing required filters for open rental quotation value calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Quotation"):
            frappe.log_error(
                "Required doctypes do not exist for open rental quotation value calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get as_of_date from filters or use today
        as_of_date = filters.get("as_of_date") or nowdate()
        
        # Get open rental quotation value
        quotation_value = frappe.db.sql("""
            SELECT SUM(grand_total) as total_value
            FROM `tabQuotation`
            WHERE company = %s
            AND status = 'Open'
            AND rental_quotation = 1
            AND valid_till >= %s
            AND docstatus = 1
        """, (filters.get("company"), as_of_date))
        
        quotation_value = flt(quotation_value[0][0]) if quotation_value and quotation_value[0][0] else 0
        
        return {"value": quotation_value}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating open rental quotation value: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_overdue_invoice_amount(filters):
    """
    Calculate the total amount of overdue rental invoices.
    
    Overdue invoice amount is the sum of all unpaid invoice amounts for rental jobs
    where the due date has passed. This KPI helps monitor accounts receivable health.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - as_of_date (str, optional): Date to check invoice status (defaults to today)
            
    Returns:
        dict: Dictionary containing the calculated overdue invoice amount:
            - value (float): Total amount of overdue rental invoices
            
    Example:
        >>> get_overdue_invoice_amount({"company": "Example Inc."})
        {'value': 8500.0}
    """
    try:
        # Validate required filters
        if not filters.get("company"):
            frappe.log_error(
                f"Missing required filters for overdue invoice amount calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Sales Invoice"):
            frappe.log_error(
                "Required doctypes do not exist for overdue invoice amount calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get as_of_date from filters or use today
        as_of_date = filters.get("as_of_date") or nowdate()
        
        # Get overdue invoice amount
        overdue_amount = frappe.db.sql("""
            SELECT SUM(outstanding_amount) as total_overdue
            FROM `tabSales Invoice`
            WHERE company = %s
            AND due_date < %s
            AND status = 'Unpaid'
            AND docstatus = 1
            AND rental_job IS NOT NULL
        """, (filters.get("company"), as_of_date))
        
        overdue_amount = flt(overdue_amount[0][0]) if overdue_amount and overdue_amount[0][0] else 0
        
        return {"value": overdue_amount}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating overdue invoice amount: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_average_revenue_per_rental_job(filters):
    """
    Calculate the average revenue per rental job.
    
    Average revenue per rental job is calculated as the total rental revenue divided
    by the number of completed rental jobs during the specified period. This KPI helps
    monitor pricing effectiveness and revenue optimization.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the calculated average revenue:
            - value (float): Average revenue per rental job
            
    Example:
        >>> get_average_revenue_per_rental_job({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {'value': 2500.0}
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for average revenue per rental job calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Sales Invoice") or not frappe.db.exists("DocType", "Rental Job"):
            frappe.log_error(
                "Required doctypes do not exist for average revenue per rental job calculation",
                "KPI Calculation Error"
            )
            return {"value": 0}
        
        # Get total rental revenue
        total_revenue = frappe.db.sql("""
            SELECT SUM(si.grand_total) as total_revenue
            FROM `tabSales Invoice` si
            WHERE si.company = %s
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
            AND si.rental_job IS NOT NULL
        """, (filters.get("company"), filters.get("from_date"), filters.get("to_date")))
        
        total_revenue = flt(total_revenue[0][0]) if total_revenue and total_revenue[0][0] else 0
        
        if total_revenue == 0:
            return {"value": 0}
        
        # Count completed rental jobs
        completed_jobs = frappe.db.count("Rental Job", {
            "company": filters.get("company"),
            "end_date": ["between", [filters.get("from_date"), filters.get("to_date")]],
            "status": "Completed",
            "docstatus": 1
        })
        
        if completed_jobs == 0:
            return {"value": 0}
        
        # Calculate average revenue per job
        average_revenue = total_revenue / completed_jobs
        
        return {"value": average_revenue}
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating average revenue per rental job: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"value": 0}

def get_rental_revenue_trend(filters):
    """
    Calculate the rental revenue trend over time.
    
    Rental revenue trend shows the monthly or weekly revenue for rental jobs over
    the specified period. This KPI helps identify seasonal patterns and growth trends.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            - group_by (str, optional): Grouping period ('Monthly' or 'Weekly', defaults to 'Monthly')
            
    Returns:
        dict: Dictionary containing the revenue trend data:
            - labels (list): List of time period labels
            - datasets (list): List containing a single dataset with:
                - name (str): Dataset name
                - values (list): Revenue values corresponding to each time period
                
    Example:
        >>> get_rental_revenue_trend({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-06-30"})
        {
            'labels': ['Jan 2023', 'Feb 2023', 'Mar 2023', 'Apr 2023', 'May 2023', 'Jun 2023'],
            'datasets': [{'name': 'Revenue', 'values': [10000, 12000, 9500, 11000, 13500, 15000]}]
        }
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for rental revenue trend calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Revenue", "values": []}]}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Sales Invoice"):
            frappe.log_error(
                "Required doctypes do not exist for rental revenue trend calculation",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Revenue", "values": []}]}
        
        # Get grouping period from filters or use default
        group_by = filters.get("group_by") or "Monthly"
        
        # Define SQL query based on grouping period
        if group_by == "Monthly":
            date_format = "%Y-%m"
            label_format = "%b %Y"
            group_by_sql = "DATE_FORMAT(posting_date, '%Y-%m')"
        else:  # Weekly
            date_format = "%Y-%u"
            label_format = "Week %u, %Y"
            group_by_sql = "DATE_FORMAT(posting_date, '%Y-%u')"
        
        # Get revenue trend data
        revenue_data = frappe.db.sql(f"""
            SELECT {group_by_sql} as period, SUM(grand_total) as revenue
            FROM `tabSales Invoice`
            WHERE company = %s
            AND posting_date BETWEEN %s AND %s
            AND docstatus = 1
            AND rental_job IS NOT NULL
            GROUP BY period
            ORDER BY period
        """, (filters.get("company"), filters.get("from_date"), filters.get("to_date")), as_dict=1)
        
        if not revenue_data:
            return {"labels": [], "datasets": [{"name": "Revenue", "values": []}]}
        
        # Format labels based on grouping period
        labels = []
        values = []
        
        for data in revenue_data:
            if group_by == "Monthly":
                year, month = data.period.split("-")
                dt = datetime(int(year), int(month), 1)
                label = dt.strftime(label_format)
            else:  # Weekly
                year, week = data.period.split("-")
                label = f"Week {week}, {year}"
            
            labels.append(label)
            values.append(data.revenue)
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "name": "Revenue",
                    "values": values
                }
            ]
        }
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating rental revenue trend: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"labels": [], "datasets": [{"name": "Revenue", "values": []}]}

def get_job_status_distribution(filters):
    """
    Calculate the distribution of rental jobs by status.
    
    Job status distribution shows the count of rental jobs in each status category.
    This KPI helps monitor the flow of jobs through the rental process.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - as_of_date (str, optional): Date to check job status (defaults to today)
            
    Returns:
        dict: Dictionary containing the job status distribution data:
            - labels (list): List of status labels
            - datasets (list): List containing a single dataset with:
                - name (str): Dataset name
                - values (list): Job counts corresponding to each status
                
    Example:
        >>> get_job_status_distribution({"company": "Example Inc."})
        {
            'labels': ['Draft', 'Confirmed', 'In Progress', 'Completed', 'Cancelled'],
            'datasets': [{'name': 'Jobs', 'values': [5, 10, 15, 50, 3]}]
        }
    """
    try:
        # Validate required filters
        if not filters.get("company"):
            frappe.log_error(
                f"Missing required filters for job status distribution calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Jobs", "values": []}]}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job"):
            frappe.log_error(
                "Required doctypes do not exist for job status distribution calculation",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Jobs", "values": []}]}
        
        # Get as_of_date from filters or use today
        as_of_date = filters.get("as_of_date") or nowdate()
        
        # Define status categories
        statuses = ["Draft", "Confirmed", "In Progress", "Completed", "Cancelled"]
        
        # Get job counts by status
        job_counts = []
        
        for status in statuses:
            count = frappe.db.count("Rental Job", {
                "company": filters.get("company"),
                "creation": ["<=", as_of_date],
                "status": status,
                "docstatus": 1 if status != "Draft" else 0
            })
            
            job_counts.append(count)
        
        return {
            "labels": statuses,
            "datasets": [
                {
                    "name": "Jobs",
                    "values": job_counts
                }
            ]
        }
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating job status distribution: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"labels": [], "datasets": [{"name": "Jobs", "values": []}]}

def get_top_5_most_rented_items(filters):
    """
    Identify the top 5 most frequently rented items.
    
    This function returns the 5 items that have been rented the most times during
    the specified period. This KPI helps identify popular items and inform inventory
    planning decisions.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the top 5 most rented items data:
            - labels (list): List of item names
            - datasets (list): List containing a single dataset with:
                - name (str): Dataset name
                - values (list): Rental counts corresponding to each item
                
    Example:
        >>> get_top_5_most_rented_items({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {
            'labels': ['Excavator', 'Generator', 'Concrete Mixer', 'Jackhammer', 'Scaffolding'],
            'datasets': [{'name': 'Rental Count', 'values': [25, 20, 18, 15, 12]}]
        }
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for top 5 most rented items calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Rental Count", "values": []}]}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job") or not frappe.db.exists("DocType", "Rental Job Item"):
            frappe.log_error(
                "Required doctypes do not exist for top 5 most rented items calculation",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Rental Count", "values": []}]}
        
        # Get top 5 most rented items
        top_items = frappe.db.sql("""
            SELECT i.item_name, COUNT(rji.name) as rental_count
            FROM `tabRental Job Item` rji
            JOIN `tabRental Job` rj ON rji.parent = rj.name
            JOIN `tabItem` i ON rji.item_code = i.name
            WHERE rj.company = %s
            AND rj.start_date BETWEEN %s AND %s
            AND rj.docstatus = 1
            GROUP BY i.item_name
            ORDER BY rental_count DESC
            LIMIT 5
        """, (filters.get("company"), filters.get("from_date"), filters.get("to_date")), as_dict=1)
        
        if not top_items:
            return {"labels": [], "datasets": [{"name": "Rental Count", "values": []}]}
        
        # Format data for chart
        labels = [item.item_name for item in top_items]
        values = [item.rental_count for item in top_items]
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "name": "Rental Count",
                    "values": values
                }
            ]
        }
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating top 5 most rented items: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"labels": [], "datasets": [{"name": "Rental Count", "values": []}]}

def get_top_5_customers_by_rental_value(filters):
    """
    Identify the top 5 customers by rental value.
    
    This function returns the 5 customers who have generated the most rental revenue
    during the specified period. This KPI helps identify key customers and inform
    customer relationship management strategies.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the top 5 customers data:
            - labels (list): List of customer names
            - datasets (list): List containing a single dataset with:
                - name (str): Dataset name
                - values (list): Rental values corresponding to each customer
                
    Example:
        >>> get_top_5_customers_by_rental_value({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {
            'labels': ['ABC Construction', 'XYZ Builders', 'City Works', 'Metro Contractors', 'Highland Developers'],
            'datasets': [{'name': 'Rental Value', 'values': [50000, 35000, 28000, 22000, 18000]}]
        }
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for top 5 customers by rental value calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Rental Value", "values": []}]}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Sales Invoice") or not frappe.db.exists("DocType", "Customer"):
            frappe.log_error(
                "Required doctypes do not exist for top 5 customers by rental value calculation",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Rental Value", "values": []}]}
        
        # Get top 5 customers by rental value
        top_customers = frappe.db.sql("""
            SELECT c.customer_name, SUM(si.grand_total) as rental_value
            FROM `tabSales Invoice` si
            JOIN `tabCustomer` c ON si.customer = c.name
            WHERE si.company = %s
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
            AND si.rental_job IS NOT NULL
            GROUP BY c.customer_name
            ORDER BY rental_value DESC
            LIMIT 5
        """, (filters.get("company"), filters.get("from_date"), filters.get("to_date")), as_dict=1)
        
        if not top_customers:
            return {"labels": [], "datasets": [{"name": "Rental Value", "values": []}]}
        
        # Format data for chart
        labels = [customer.customer_name for customer in top_customers]
        values = [customer.rental_value for customer in top_customers]
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "name": "Rental Value",
                    "values": values
                }
            ]
        }
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating top 5 customers by rental value: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"labels": [], "datasets": [{"name": "Rental Value", "values": []}]}

def get_damage_rate_by_item_group(filters):
    """
    Calculate the damage rate for each item group.
    
    Damage rate by item group shows the percentage of rental jobs where items in each
    group were returned with damage. This KPI helps identify item groups that may
    require more robust construction or better handling instructions.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            
    Returns:
        dict: Dictionary containing the damage rate by item group data:
            - labels (list): List of item group names
            - datasets (list): List containing a single dataset with:
                - name (str): Dataset name
                - values (list): Damage rates corresponding to each item group
                
    Example:
        >>> get_damage_rate_by_item_group({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-01-31"})
        {
            'labels': ['Heavy Equipment', 'Tools', 'Vehicles', 'Electronics', 'Furniture'],
            'datasets': [{'name': 'Damage Rate (%)', 'values': [12.5, 8.3, 15.0, 5.2, 3.7]}]
        }
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for damage rate by item group calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Damage Rate (%)", "values": []}]}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job") or not frappe.db.exists("DocType", "Item"):
            frappe.log_error(
                "Required doctypes do not exist for damage rate by item group calculation",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Damage Rate (%)", "values": []}]}
        
        # Get item groups
        item_groups = frappe.db.sql("""
            SELECT DISTINCT i.item_group
            FROM `tabRental Job Item` rji
            JOIN `tabRental Job` rj ON rji.parent = rj.name
            JOIN `tabItem` i ON rji.item_code = i.name
            WHERE rj.company = %s
            AND rj.end_date BETWEEN %s AND %s
            AND rj.status = 'Completed'
            AND rj.docstatus = 1
        """, (filters.get("company"), filters.get("from_date"), filters.get("to_date")), as_dict=1)
        
        if not item_groups:
            return {"labels": [], "datasets": [{"name": "Damage Rate (%)", "values": []}]}
        
        # Calculate damage rate for each item group
        labels = []
        damage_rates = []
        
        for group in item_groups:
            # Count total rentals for this item group
            total_rentals = frappe.db.sql("""
                SELECT COUNT(DISTINCT rj.name) as count
                FROM `tabRental Job Item` rji
                JOIN `tabRental Job` rj ON rji.parent = rj.name
                JOIN `tabItem` i ON rji.item_code = i.name
                WHERE rj.company = %s
                AND rj.end_date BETWEEN %s AND %s
                AND rj.status = 'Completed'
                AND rj.docstatus = 1
                AND i.item_group = %s
            """, (filters.get("company"), filters.get("from_date"), filters.get("to_date"), group.item_group))
            
            total_count = cint(total_rentals[0][0]) if total_rentals and total_rentals[0][0] else 0
            
            if total_count == 0:
                continue
            
            # Count damaged rentals for this item group
            damaged_rentals = frappe.db.sql("""
                SELECT COUNT(DISTINCT rj.name) as count
                FROM `tabRental Job Item` rji
                JOIN `tabRental Job` rj ON rji.parent = rj.name
                JOIN `tabItem` i ON rji.item_code = i.name
                WHERE rj.company = %s
                AND rj.end_date BETWEEN %s AND %s
                AND rj.status = 'Completed'
                AND rj.docstatus = 1
                AND rj.has_damaged_items = 1
                AND i.item_group = %s
            """, (filters.get("company"), filters.get("from_date"), filters.get("to_date"), group.item_group))
            
            damaged_count = cint(damaged_rentals[0][0]) if damaged_rentals and damaged_rentals[0][0] else 0
            
            # Calculate damage rate
            damage_rate = (damaged_count / total_count) * 100
            
            labels.append(group.item_group)
            damage_rates.append(damage_rate)
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "name": "Damage Rate (%)",
                    "values": damage_rates
                }
            ]
        }
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating damage rate by item group: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"labels": [], "datasets": [{"name": "Damage Rate (%)", "values": []}]}

def get_item_utilization_rate_trend(filters):
    """
    Calculate the item utilization rate trend over time.
    
    Item utilization rate trend shows the monthly or weekly utilization rate for
    rental items over the specified period. This KPI helps identify seasonal patterns
    and optimization opportunities.
    
    Args:
        filters (dict): Dictionary containing filter parameters:
            - company (str): Company name
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            - group_by (str, optional): Grouping period ('Monthly' or 'Weekly', defaults to 'Monthly')
            
    Returns:
        dict: Dictionary containing the utilization rate trend data:
            - labels (list): List of time period labels
            - datasets (list): List containing a single dataset with:
                - name (str): Dataset name
                - values (list): Utilization rates corresponding to each time period
                
    Example:
        >>> get_item_utilization_rate_trend({"company": "Example Inc.", "from_date": "2023-01-01", "to_date": "2023-06-30"})
        {
            'labels': ['Jan 2023', 'Feb 2023', 'Mar 2023', 'Apr 2023', 'May 2023', 'Jun 2023'],
            'datasets': [{'name': 'Utilization Rate (%)', 'values': [65.0, 70.5, 68.2, 72.1, 75.3, 78.0]}]
        }
    """
    try:
        # Validate required filters
        if not filters.get("company") or not filters.get("from_date") or not filters.get("to_date"):
            frappe.log_error(
                f"Missing required filters for item utilization rate trend calculation: {filters}",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Utilization Rate (%)", "values": []}]}
        
        # Verify schema requirements
        if not frappe.db.exists("DocType", "Rental Job") or not frappe.db.exists("DocType", "Item"):
            frappe.log_error(
                "Required doctypes do not exist for item utilization rate trend calculation",
                "KPI Calculation Error"
            )
            return {"labels": [], "datasets": [{"name": "Utilization Rate (%)", "values": []}]}
        
        # Get grouping period from filters or use default
        group_by = filters.get("group_by") or "Monthly"
        
        # Parse from_date and to_date
        from_date = getdate(filters.get("from_date"))
        to_date = getdate(filters.get("to_date"))
        
        # Generate time periods
        periods = []
        labels = []
        
        if group_by == "Monthly":
            # Generate monthly periods
            current_date = from_date.replace(day=1)
            while current_date <= to_date:
                period_end = current_date.replace(day=calendar.monthrange(current_date.year, current_date.month)[1])
                periods.append({
                    "start_date": current_date,
                    "end_date": period_end,
                    "label": current_date.strftime("%b %Y")
                })
                labels.append(current_date.strftime("%b %Y"))
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
        else:  # Weekly
            # Generate weekly periods
            current_date = from_date
            # Move to the beginning of the week (Monday)
            current_date = current_date - timedelta(days=current_date.weekday())
            
            while current_date <= to_date:
                period_end = current_date + timedelta(days=6)
                week_num = current_date.isocalendar()[1]
                periods.append({
                    "start_date": current_date,
                    "end_date": period_end,
                    "label": f"Week {week_num}, {current_date.year}"
                })
                labels.append(f"Week {week_num}, {current_date.year}")
                
                # Move to next week
                current_date = current_date + timedelta(days=7)
        
        # Calculate utilization rate for each period
        utilization_rates = []
        
        for period in periods:
            period_filters = {
                "company": filters.get("company"),
                "from_date": period["start_date"].strftime("%Y-%m-%d"),
                "to_date": period["end_date"].strftime("%Y-%m-%d")
            }
            
            # Calculate utilization rate for this period
            result = calculate_item_utilization_rate(period_filters)
            utilization_rates.append(result["value"])
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "name": "Utilization Rate (%)",
                    "values": utilization_rates
                }
            ]
        }
    
    except Exception as e:
        frappe.log_error(
            f"Error calculating item utilization rate trend: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        return {"labels": [], "datasets": [{"name": "Utilization Rate (%)", "values": []}]}
