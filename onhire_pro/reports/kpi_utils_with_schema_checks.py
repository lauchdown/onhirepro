import frappe
from frappe.utils import nowdate, add_days, date_diff, getdate, add_months
from onhire_pro.utils.schema_verifier import verify_schema_for_kpi, get_safe_value_for_kpi

def calculate_item_utilization_rate(filters=None):
    """
    Calculate the utilization rate of rental items.
    
    Args:
        filters (dict, optional): Filters to apply to the calculation
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            - item_group (str, optional): Filter by item group
            - company (str, optional): Filter by company
    
    Returns:
        dict: {"value": utilization_rate_percentage}
    """
    # Verify schema requirements
    schema_check = verify_schema_for_kpi("item_utilization_rate")
    if schema_check["status"] != "valid":
        frappe.log_error(
            f"Schema verification failed for item_utilization_rate: {schema_check['message']}",
            "KPI Schema Error"
        )
        return get_safe_value_for_kpi("item_utilization_rate")
    
    if not filters:
        filters = {}
        
    # Default to last 30 days if not specified
    from_date = filters.get("from_date") or add_days(nowdate(), -30)
    to_date = filters.get("to_date") or nowdate()
    company = filters.get("company") or frappe.defaults.get_user_default("company")
    item_group = filters.get("item_group")
    
    try:
        # Calculate total available time for all rental items
        item_filter = ""
        if item_group:
            item_filter = f"AND i.item_group = '{item_group}'"
            
        # Get all rental items and their quantities
        items_query = f"""
            SELECT 
                i.name as item_code,
                IFNULL(SUM(b.actual_qty), 0) as available_qty
            FROM 
                `tabItem` i
            LEFT JOIN 
                `tabBin` b ON b.item_code = i.name
            WHERE 
                i.is_rental_item = 1
                AND i.disabled = 0
                AND i.company = '{company}'
                {item_filter}
            GROUP BY 
                i.name
        """
        
        items = frappe.db.sql(items_query, as_dict=True)
        
        if not items:
            return {"value": 0}
        
        # Calculate total available time (days * quantity)
        total_days = date_diff(to_date, from_date)
        total_available_time = sum(item.available_qty * total_days for item in items)
        
        if total_available_time <= 0:
            return {"value": 0}
        
        # Get rental time for each item
        rental_query = f"""
            SELECT 
                rji.item_code,
                SUM(
                    LEAST(
                        DATEDIFF(
                            LEAST(rj.actual_return_date, '{to_date}', IFNULL(rj.rental_end_date, '{to_date}')),
                            GREATEST(rj.rental_start_date, '{from_date}')
                        ) + 1, 
                        0
                    ) * rji.qty
                ) as rented_days
            FROM 
                `tabRental Job` rj
            JOIN 
                `tabRental Job Item` rji ON rji.parent = rj.name
            JOIN 
                `tabItem` i ON i.name = rji.item_code
            WHERE 
                rj.docstatus = 1
                AND rj.company = '{company}'
                AND rj.rental_start_date <= '{to_date}'
                AND (rj.rental_end_date >= '{from_date}' OR rj.actual_return_date >= '{from_date}')
                {item_filter}
            GROUP BY 
                rji.item_code
        """
        
        rental_data = frappe.db.sql(rental_query, as_dict=True)
        
        # Calculate total rented time
        total_rented_time = sum(item.rented_days for item in rental_data)
        
        # Calculate utilization rate
        utilization_rate = (total_rented_time / total_available_time) * 100
        
        # Cap at 100% for logical presentation
        utilization_rate = min(utilization_rate, 100)
        
        return {"value": round(utilization_rate, 2)}
    except Exception as e:
        frappe.log_error(
            f"Error in calculate_item_utilization_rate: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        # Return safe default value
        return {"value": 0}

def calculate_average_rental_duration(filters=None):
    """
    Calculate the average duration of rental jobs.
    
    Args:
        filters (dict, optional): Filters to apply to the calculation
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            - company (str, optional): Filter by company
    
    Returns:
        dict: {"value": average_duration_days}
    """
    # Verify schema requirements
    schema_check = verify_schema_for_kpi("average_rental_duration")
    if schema_check["status"] != "valid":
        frappe.log_error(
            f"Schema verification failed for average_rental_duration: {schema_check['message']}",
            "KPI Schema Error"
        )
        return get_safe_value_for_kpi("average_rental_duration")
    
    if not filters:
        filters = {}
        
    # Default to last 30 days if not specified
    from_date = filters.get("from_date") or add_days(nowdate(), -30)
    to_date = filters.get("to_date") or nowdate()
    company = filters.get("company") or frappe.defaults.get_user_default("company")
    
    try:
        # Query to calculate average rental duration for completed rentals
        query = f"""
            SELECT 
                AVG(
                    DATEDIFF(
                        IFNULL(actual_return_date, rental_end_date),
                        rental_start_date
                    ) + 1
                ) as avg_duration
            FROM 
                `tabRental Job`
            WHERE 
                docstatus = 1
                AND company = '{company}'
                AND status IN ('Completed', 'Closed')
                AND rental_start_date <= '{to_date}'
                AND (
                    (actual_return_date IS NOT NULL AND actual_return_date >= '{from_date}')
                    OR
                    (actual_return_date IS NULL AND rental_end_date >= '{from_date}')
                )
        """
        
        result = frappe.db.sql(query, as_dict=True)
        avg_duration = result[0].avg_duration if result and result[0].avg_duration else 0
        
        # Round to 1 decimal place for better readability
        return {"value": round(float(avg_duration), 1)}
    except Exception as e:
        frappe.log_error(
            f"Error in calculate_average_rental_duration: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        # Return safe default value
        return {"value": 0}

def get_revenue_per_item_category(filters=None):
    """
    Calculate revenue per item category for the specified period.
    
    Args:
        filters (dict, optional): Filters to apply to the calculation
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            - company (str, optional): Filter by company
    
    Returns:
        dict: {"labels": [category_names], "datasets": [{"name": "Revenue", "values": [values]}]}
    """
    # Verify schema requirements
    schema_check = verify_schema_for_kpi("revenue_per_item_category")
    if schema_check["status"] != "valid":
        frappe.log_error(
            f"Schema verification failed for revenue_per_item_category: {schema_check['message']}",
            "KPI Schema Error"
        )
        return get_safe_value_for_kpi("revenue_per_item_category")
    
    if not filters:
        filters = {}
        
    # Default to last 30 days if not specified
    from_date = filters.get("from_date") or add_days(nowdate(), -30)
    to_date = filters.get("to_date") or nowdate()
    company = filters.get("company") or frappe.defaults.get_user_default("company")
    
    try:
        # Query to get revenue by item category
        query = f"""
            SELECT 
                i.item_group as category,
                SUM(rji.amount) as revenue
            FROM 
                `tabRental Job` rj
            JOIN 
                `tabRental Job Item` rji ON rji.parent = rj.name
            JOIN 
                `tabItem` i ON i.name = rji.item_code
            WHERE 
                rj.docstatus = 1
                AND rj.company = '{company}'
                AND rj.rental_start_date <= '{to_date}'
                AND (rj.rental_end_date >= '{from_date}' OR rj.actual_return_date >= '{from_date}')
            GROUP BY 
                i.item_group
            ORDER BY 
                revenue DESC
            LIMIT 10
        """
        
        result = frappe.db.sql(query, as_dict=True)
        
        if not result:
            # Return empty dataset if no data
            return {
                "labels": [],
                "datasets": [{"name": "Revenue", "values": []}]
            }
        
        # Extract categories and revenues
        categories = [row.category for row in result]
        revenues = [row.revenue for row in result]
        
        return {
            "labels": categories,
            "datasets": [
                {
                    "name": "Revenue",
                    "values": revenues
                }
            ]
        }
    except Exception as e:
        frappe.log_error(
            f"Error in get_revenue_per_item_category: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        # Return empty dataset on error
        return {
            "labels": [],
            "datasets": [{"name": "Revenue", "values": []}]
        }

def calculate_avg_maintenance_turnaround_time(filters=None):
    """
    Calculate the average time taken to complete maintenance tasks.
    
    Args:
        filters (dict, optional): Filters to apply to the calculation
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            - company (str, optional): Filter by company
    
    Returns:
        dict: {"value": average_turnaround_time_days}
    """
    # Verify schema requirements
    schema_check = verify_schema_for_kpi("maintenance_turnaround_time")
    if schema_check["status"] != "valid":
        frappe.log_error(
            f"Schema verification failed for maintenance_turnaround_time: {schema_check['message']}",
            "KPI Schema Error"
        )
        return get_safe_value_for_kpi("maintenance_turnaround_time")
    
    if not filters:
        filters = {}
        
    # Default to last 30 days if not specified
    from_date = filters.get("from_date") or add_days(nowdate(), -30)
    to_date = filters.get("to_date") or nowdate()
    company = filters.get("company") or frappe.defaults.get_user_default("company")
    
    try:
        # Query to calculate average maintenance turnaround time
        query = f"""
            SELECT 
                AVG(
                    DATEDIFF(
                        completion_date,
                        start_date
                    ) + 1
                ) as avg_turnaround_time
            FROM 
                `tabMaintenance Task`
            WHERE 
                docstatus = 1
                AND company = '{company}'
                AND status = 'Completed'
                AND start_date <= '{to_date}'
                AND completion_date >= '{from_date}'
                AND completion_date IS NOT NULL
        """
        
        result = frappe.db.sql(query, as_dict=True)
        avg_turnaround_time = result[0].avg_turnaround_time if result and result[0].avg_turnaround_time else 0
        
        # Round to 1 decimal place for better readability
        return {"value": round(float(avg_turnaround_time), 1)}
    except Exception as e:
        frappe.log_error(
            f"Error in calculate_avg_maintenance_turnaround_time: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        # Return safe default value
        return {"value": 0}

def calculate_booking_conversion_rate(filters=None):
    """
    Calculate the rate at which rental quotations convert to confirmed bookings.
    
    Args:
        filters (dict, optional): Filters to apply to the calculation
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            - company (str, optional): Filter by company
    
    Returns:
        dict: {"value": conversion_rate_percentage}
    """
    # Verify schema requirements
    schema_check = verify_schema_for_kpi("booking_conversion_rate")
    if schema_check["status"] != "valid":
        frappe.log_error(
            f"Schema verification failed for booking_conversion_rate: {schema_check['message']}",
            "KPI Schema Error"
        )
        return get_safe_value_for_kpi("booking_conversion_rate")
    
    if not filters:
        filters = {}
        
    # Default to last 30 days if not specified
    from_date = filters.get("from_date") or add_days(nowdate(), -30)
    to_date = filters.get("to_date") or nowdate()
    company = filters.get("company") or frappe.defaults.get_user_default("company")
    
    try:
        # Query to count total rental quotations in the period
        quotations_query = f"""
            SELECT 
                COUNT(*) as total_quotations
            FROM 
                `tabQuotation` q
            WHERE 
                q.docstatus = 1
                AND q.company = '{company}'
                AND q.transaction_date BETWEEN '{from_date}' AND '{to_date}'
                AND q.is_rental_quotation = 1
        """
        
        # Query to count converted quotations (those that led to rental jobs)
        converted_query = f"""
            SELECT 
                COUNT(DISTINCT q.name) as converted_quotations
            FROM 
                `tabQuotation` q
            JOIN 
                `tabRental Job` rj ON rj.quotation = q.name
            WHERE 
                q.docstatus = 1
                AND q.company = '{company}'
                AND q.transaction_date BETWEEN '{from_date}' AND '{to_date}'
                AND q.is_rental_quotation = 1
                AND rj.docstatus = 1
        """
        
        # Execute queries
        quotations_result = frappe.db.sql(quotations_query, as_dict=True)
        converted_result = frappe.db.sql(converted_query, as_dict=True)
        
        # Extract counts
        total_quotations = quotations_result[0].total_quotations if quotations_result else 0
        converted_quotations = converted_result[0].converted_quotations if converted_result else 0
        
        # Calculate conversion rate
        if total_quotations > 0:
            conversion_rate = (converted_quotations / total_quotations) * 100
        else:
            conversion_rate = 0
        
        return {"value": round(conversion_rate, 2)}
    except Exception as e:
        frappe.log_error(
            f"Error in calculate_booking_conversion_rate: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        # Return safe default value
        return {"value": 0}

def get_stock_reservation_conflicts(filters=None):
    """
    Get count of stock reservation conflicts where items are double-booked.
    
    Args:
        filters (dict, optional): Filters to apply to the calculation
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            - company (str, optional): Filter by company
    
    Returns:
        dict: {"value": conflict_count}
    """
    # Verify schema requirements
    schema_check = verify_schema_for_kpi("stock_reservation_conflicts")
    if schema_check["status"] != "valid":
        frappe.log_error(
            f"Schema verification failed for stock_reservation_conflicts: {schema_check['message']}",
            "KPI Schema Error"
        )
        return get_safe_value_for_kpi("stock_reservation_conflicts")
    
    if not filters:
        filters = {}
        
    # Default to next 30 days if not specified (looking forward for conflicts)
    from_date = filters.get("from_date") or nowdate()
    to_date = filters.get("to_date") or add_days(nowdate(), 30)
    company = filters.get("company") or frappe.defaults.get_user_default("company")
    
    try:
        # Query to find overlapping rental periods for the same items
        query = f"""
            SELECT 
                COUNT(DISTINCT r1.name) as conflict_count
            FROM 
                `tabRental Job` r1
            JOIN 
                `tabRental Job Item` i1 ON i1.parent = r1.name
            JOIN 
                `tabRental Job` r2 ON r2.name != r1.name
            JOIN 
                `tabRental Job Item` i2 ON i2.parent = r2.name AND i2.item_code = i1.item_code
            WHERE 
                r1.docstatus = 1
                AND r2.docstatus = 1
                AND r1.company = '{company}'
                AND r2.company = '{company}'
                AND r1.status NOT IN ('Completed', 'Cancelled')
                AND r2.status NOT IN ('Completed', 'Cancelled')
                AND r1.rental_start_date <= '{to_date}'
                AND r1.rental_end_date >= '{from_date}'
                AND r2.rental_start_date <= '{to_date}'
                AND r2.rental_end_date >= '{from_date}'
                AND (
                    (r1.rental_start_date BETWEEN r2.rental_start_date AND r2.rental_end_date)
                    OR
                    (r1.rental_end_date BETWEEN r2.rental_start_date AND r2.rental_end_date)
                    OR
                    (r2.rental_start_date BETWEEN r1.rental_start_date AND r1.rental_end_date)
                    OR
                    (r2.rental_end_date BETWEEN r1.rental_start_date AND r1.rental_end_date)
                )
                AND (i1.qty + i2.qty) > (
                    SELECT IFNULL(SUM(actual_qty), 0)
                    FROM `tabBin`
                    WHERE item_code = i1.item_code
                )
        """
        
        result = frappe.db.sql(query, as_dict=True)
        conflict_count = result[0].conflict_count if result and result[0].conflict_count else 0
        
        return {"value": int(conflict_count)}
    except Exception as e:
        frappe.log_error(
            f"Error in get_stock_reservation_conflicts: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        # Return safe default value
        return {"value": 0}

def get_overdue_returns_count(filters=None):
    """
    Get count of rental jobs with overdue returns.
    
    Args:
        filters (dict, optional): Filters to apply to the calculation
            - company (str, optional): Filter by company
    
    Returns:
        dict: {"value": overdue_count}
    """
    # Verify schema requirements
    schema_check = verify_schema_for_kpi("overdue_returns_count")
    if schema_check["status"] != "valid":
        frappe.log_error(
            f"Schema verification failed for overdue_returns_count: {schema_check['message']}",
            "KPI Schema Error"
        )
        return get_safe_value_for_kpi("overdue_returns_count")
    
    if not filters:
        filters = {}
        
    company = filters.get("company") or frappe.defaults.get_user_default("company")
    current_date = nowdate()
    
    try:
        # Query to count rental jobs with overdue returns
        query = f"""
            SELECT 
                COUNT(*) as overdue_count
            FROM 
                `tabRental Job`
            WHERE 
                docstatus = 1
                AND company = '{company}'
                AND status = 'Active'
                AND rental_end_date < '{current_date}'
                AND actual_return_date IS NULL
        """
        
        result = frappe.db.sql(query, as_dict=True)
        overdue_count = result[0].overdue_count if result and result[0].overdue_count else 0
        
        return {"value": int(overdue_count)}
    except Exception as e:
        frappe.log_error(
            f"Error in get_overdue_returns_count: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        # Return safe default value
        return {"value": 0}

def get_active_rental_jobs_count(filters=None):
    """
    Get count of currently active rental jobs.
    
    Args:
        filters (dict, optional): Filters to apply to the calculation
            - company (str, optional): Filter by company
    
    Returns:
        dict: {"value": active_jobs_count}
    """
    # Verify schema requirements
    schema_check = verify_schema_for_kpi("active_rental_jobs_count")
    if schema_check["status"] != "valid":
        frappe.log_error(
            f"Schema verification failed for active_rental_jobs_count: {schema_check['message']}",
            "KPI Schema Error"
        )
        return get_safe_value_for_kpi("active_rental_jobs_count")
    
    if not filters:
        filters = {}
        
    company = filters.get("company") or frappe.defaults.get_user_default("company")
    current_date = nowdate()
    
    try:
        # Query to count active rental jobs
        query = f"""
            SELECT 
                COUNT(*) as active_count
            FROM 
                `tabRental Job`
            WHERE 
                docstatus = 1
                AND company = '{company}'
                AND status = 'Active'
                AND rental_start_date <= '{current_date}'
                AND (rental_end_date >= '{current_date}' OR actual_return_date IS NULL)
        """
        
        result = frappe.db.sql(query, as_dict=True)
        active_count = result[0].active_count if result and result[0].active_count else 0
        
        return {"value": int(active_count)}
    except Exception as e:
        frappe.log_error(
            f"Error in get_active_rental_jobs_count: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        # Return safe default value
        return {"value": 0}

def calculate_active_rental_jobs(filters=None):
    """
    Alias for get_active_rental_jobs_count for backward compatibility.
    """
    return get_active_rental_jobs_count(filters)

def get_total_rental_revenue(filters=None):
    """
    Get total rental revenue for the specified period.
    
    Args:
        filters (dict, optional): Filters to apply to the calculation
            - from_date (str): Start date for calculation period
            - to_date (str): End date for calculation period
            - company (str, optional): Filter by company
            - compare_previous (bool, optional): Whether to include previous period comparison
    
    Returns:
        dict: {"value": total_revenue, "previous_value": previous_revenue, "change_percentage": change_percentage}
    """
    # Verify schema requirements
    schema_check = verify_schema_for_kpi("total_rental_revenue")
    if schema_check["status"] != "valid":
        frappe.log_error(
            f"Schema verification failed for total_rental_revenue: {schema_check['message']}",
            "KPI Schema Error"
        )
        return get_safe_value_for_kpi("total_rental_revenue")
    
    if not filters:
        filters = {}
        
    # Default to current month if not specified
    current_date = getdate(nowdate())
    from_date = filters.get("from_date") or getdate(f"{current_date.year}-{current_date.month}-01")
    to_date = filters.get("to_date") or getdate(add_days(add_months(from_date, 1), -1))
    company = filters.get("company") or frappe.defaults.get_user_default("company")
    compare_previous = filters.get("compare_previous") or True
    
    try:
        # Query to get total revenue for current period
        current_query = f"""
            SELECT 
                SUM(grand_total) as total_revenue
            FROM 
                `tabSales Invoice`
            WHERE 
                docstatus = 1
                AND company = '{company}'
                AND posting_date BETWEEN '{from_date}' AND '{to_date}'
                AND is_rental_invoice = 1
        """
        
        current_result = frappe.db.sql(current_query, as_dict=True)
        current_revenue = current_result[0].total_revenue if current_result and current_result[0].total_revenue else 0
        
        # If comparison is requested, calculate previous period
        if compare_previous:
            # Calculate previous period dates (same duration)
            period_days = date_diff(to_date, from_date) + 1
            prev_to_date = add_days(from_date, -1)
            prev_from_date = add_days(prev_to_date, -period_days + 1)
            
            # Query for previous period
            previous_query = f"""
                SELECT 
                    SUM(grand_total) as total_revenue
                FROM 
                    `tabSales Invoice`
                WHERE 
                    docstatus = 1
                    AND company = '{company}'
                    AND posting_date BETWEEN '{prev_from_date}' AND '{prev_to_date}'
                    AND is_rental_invoice = 1
            """
            
            previous_result = frappe.db.sql(previous_query, as_dict=True)
            previous_revenue = previous_result[0].total_revenue if previous_result and previous_result[0].total_revenue else 0
            
            # Calculate change percentage
            if previous_revenue > 0:
                change_percentage = ((current_revenue - previous_revenue) / previous_revenue) * 100
            else:
                change_percentage = 100 if current_revenue > 0 else 0
                
            return {
                "value": round(float(current_revenue), 2),
                "previous_value": round(float(previous_revenue), 2),
                "change_percentage": round(change_percentage, 2)
            }
        else:
            return {"value": round(float(current_revenue), 2)}
    except Exception as e:
        frappe.log_error(
            f"Error in get_total_rental_revenue: {str(e)}\n{frappe.get_traceback()}",
            "KPI Calculation Error"
        )
        # Return safe default value
        return {"value": 0}
