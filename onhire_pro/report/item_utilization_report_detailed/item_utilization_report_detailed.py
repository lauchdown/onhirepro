# Project/onhire_pro/onhire_pro/report/item_utilization_report_detailed/item_utilization_report_detailed.py
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, add_days, date_diff, flt, add_months, get_first_day, get_last_day
# Assuming kpi_utils.py is in a discoverable path, e.g., same app or PYTHONPATH
# For direct relative import if in same app: from ..kpi_utils import calculate_item_utilization_rate
# If kpi_utils is in onhire_pro.onhire_pro.reports then:
from onhire_pro.onhire_pro.reports.kpi_utils import calculate_item_utilization_rate 

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    columns = [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 120}
    ]
    if filters.get("summarize_by") and filters.get("summarize_by") != "Overall":
        columns.append({"label": _("Period"), "fieldname": "period", "fieldtype": "Data", "width": 120})
    
    columns.extend([
        {"label": _("Total Rented Qty*Days"), "fieldname": "total_rented_qty_days", "fieldtype": "Float", "width": 180, "description": _("Sum of (Quantity Rented * Days Rented in Period)")},
        {"label": _("Total Available Qty*Days"), "fieldname": "total_available_qty_days", "fieldtype": "Float", "width": 180, "description": _("Sum of (Available Quantity * Days in Period)")},
        {"label": _("Utilization Rate (%)"), "fieldname": "utilization_rate", "fieldtype": "Percent", "width": 150}
    ])
    return columns

def get_data(filters):
    data = []
    company = filters.get("company")
    from_date_main = getdate(filters.get("from_date"))
    to_date_main = getdate(filters.get("to_date"))
    item_code_filter = filters.get("item_code")
    item_group_filter = filters.get("item_group")
    summarize_by = filters.get("summarize_by", "Monthly") 

    item_q_filters = {"is_rental_item": 1, "disabled": 0}
    # Company filter for items might not be standard, depends on Item master setup
    # If items are not company-specific, this filter might be removed or adapted
    if company and frappe.db.has_column("Item", "company"):
         item_q_filters["company"] = company

    if item_code_filter:
        item_q_filters["name"] = item_code_filter
    if item_group_filter:
        item_q_filters["item_group"] = item_group_filter
    
    items_to_report = frappe.get_all("Item", filters=item_q_filters, fields=["name", "item_name", "item_group"])

    if summarize_by == "Overall" or not summarize_by:
        for item in items_to_report:
            period_days = date_diff(to_date_main, from_date_main) + 1
            rented_qty_days, available_qty_days, util_rate = get_utilization_components(
                item.name, from_date_main, to_date_main, company, period_days
            )
            data.append({
                "item_code": item.name, "item_name": item.item_name, "item_group": item.item_group,
                "total_rented_qty_days": rented_qty_days,
                "total_available_qty_days": available_qty_days,
                "utilization_rate": util_rate
            })
    else: 
        periods = get_periods(from_date_main, to_date_main, summarize_by)
        for item in items_to_report:
            for period_start, period_end, period_label in periods:
                sub_period_days = date_diff(period_end, period_start) + 1
                rented_qty_days, available_qty_days, util_rate = get_utilization_components(
                    item.name, period_start, period_end, company, sub_period_days
                )
                data.append({
                    "item_code": item.name, "item_name": item.item_name, "item_group": item.item_group,
                    "period": period_label,
                    "total_rented_qty_days": rented_qty_days,
                    "total_available_qty_days": available_qty_days,
                    "utilization_rate": util_rate
                })
    return data

def get_utilization_components(item_code, from_date, to_date, company, period_days):
    sql_params_item = {
        "from_date": from_date, "to_date": to_date, 
        "company": company, "item_code": item_code
    }
    rented_sum_q = """SELECT SUM((DATEDIFF(LEAST(rj.scheduled_return_date, %(to_date)s), GREATEST(rj.scheduled_dispatch_date, %(from_date)s)) + 1) * rji.qty) 
                      FROM `tabRental Job Item` rji JOIN `tabRental Job` rj ON rji.parent = rj.name
                      WHERE rj.docstatus = 1 AND rj.status NOT IN ('Cancelled', 'Draft') AND rj.company = %(company)s
                        AND rj.scheduled_dispatch_date <= %(to_date)s AND rj.scheduled_return_date >= %(from_date)s
                        AND rji.item_code = %(item_code)s"""
    total_rented_qty_days_res = frappe.db.sql(rented_sum_q, sql_params_item)
    total_rented_qty_days = total_rented_qty_days_res[0][0] or 0 if total_rented_qty_days_res and total_rented_qty_days_res[0] else 0
    
    item_doc = frappe.get_doc("Item", item_code)
    total_available_qty_days = 0
    if item_doc.has_serial_no:
        num_serials = frappe.db.count("Serial No", {"item_code": item_code, "status": ["!=", "Scrapped"]})
        total_available_qty_days = num_serials * period_days
    else:
        try:
            from erpnext.stock.utils import get_projected_qty as get_erpnext_projected_qty
            # Determine warehouse: use item's default, or company default, or a specific rental warehouse from settings
            warehouse_to_check = item_doc.default_warehouse or frappe.db.get_single_value("Stock Settings", "default_warehouse")
            # Potentially override with a specific rental fleet warehouse from Rental Settings
            # rental_fleet_warehouse = frappe.db.get_single_value("Rental Settings", "default_rental_fleet_warehouse")
            # if rental_fleet_warehouse: warehouse_to_check = rental_fleet_warehouse
            
            if warehouse_to_check and get_erpnext_projected_qty:
                # get_projected_qty for a period is complex. Using qty at start of period as proxy.
                avg_stock = get_erpnext_projected_qty(item_code, warehouse_to_check, from_date) 
                total_available_qty_days = avg_stock * period_days
            else: total_available_qty_days = (item_doc.total_projected_qty or 1) * period_days
        except ImportError: 
            frappe.log_info("erpnext.stock.utils.get_projected_qty not found. Using fallback for utilization.", "ItemUtilizationReport")
            total_available_qty_days = (item_doc.total_projected_qty or 1) * period_days
        except Exception as e:
            frappe.log_error(f"Error getting projected qty for {item_code}: {e}", "ItemUtilizationReport")
            total_available_qty_days = (item_doc.total_projected_qty or 1) * period_days


    util_rate = (total_rented_qty_days / total_available_qty_days * 100) if total_available_qty_days else 0.0
    return total_rented_qty_days, total_available_qty_days, round(min(util_rate, 100),2)

def get_periods(from_date, to_date, summarize_by):
    periods = []
    current_period_start = getdate(from_date)
    end_date_final = getdate(to_date)

    while current_period_start <= end_date_final:
        period_label = ""
        if summarize_by == "Daily":
            period_end = current_period_start
            period_label = current_period_start.strftime("%Y-%m-%d")
            next_period_start = add_days(current_period_start, 1)
        elif summarize_by == "Weekly":
            period_end = add_days(current_period_start, 6)
            if period_end > end_date_final: period_end = end_date_final
            period_label = f"{current_period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}"
            next_period_start = add_days(period_end, 1)
        elif summarize_by == "Monthly":
            period_start_actual = get_first_day(current_period_start) # Ensure it's actual start of month
            period_end = get_last_day(period_start_actual)
            if period_end > end_date_final: period_end = end_date_final
            if period_start_actual > end_date_final : break 
            period_label = period_start_actual.strftime("%b %Y")
            next_period_start = add_months(period_start_actual, 1)
            current_period_start = period_start_actual # Align current_period_start for the loop
        elif summarize_by == "Quarterly":
            month = current_period_start.month
            year = current_period_start.year
            if month <= 3: quarter_start_month = 1
            elif month <= 6: quarter_start_month = 4
            elif month <= 9: quarter_start_month = 7
            else: quarter_start_month = 10
            period_start_actual = getdate(f"{year}-{quarter_start_month:02d}-01")
            period_end = get_last_day(add_months(period_start_actual, 2))
            if period_end > end_date_final: period_end = end_date_final
            if period_start_actual > end_date_final : break
            period_label = f"Q{(quarter_start_month-1)//3 + 1} {year}"
            next_period_start = add_months(period_start_actual, 3)
            current_period_start = period_start_actual
        elif summarize_by == "Yearly":
            period_start_actual = get_first_day(current_period_start).replace(month=1, day=1)
            period_end = get_last_day(current_period_start).replace(month=12, day=31)
            if period_end > end_date_final: period_end = end_date_final
            if period_start_actual > end_date_final : break
            period_label = period_start_actual.strftime("%Y")
            next_period_start = add_months(period_start_actual, 12)
            current_period_start = period_start_actual
        else:
            break 
        
        periods.append((current_period_start, period_end, period_label))
        current_period_start = next_period_start
            
    return periods
