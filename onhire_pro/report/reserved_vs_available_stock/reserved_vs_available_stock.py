# Project/onhire_pro/onhire_pro/report/reserved_vs_available_stock/reserved_vs_available_stock.py
import frappe
from frappe import _
from frappe.utils import getdate, flt, nowdate

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 150
        },
        {
            "label": _("Actual Qty"),
            "fieldname": "actual_qty",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Reserved Qty (Rental Jobs)"),
            "fieldname": "reserved_qty_rental_jobs",
            "fieldtype": "Float",
            "width": 180,
            "description": _("Quantity reserved for active/confirmed Rental Jobs overlapping the 'To Date'")
        },
        # Add other reservation sources if applicable (e.g., Sales Orders)
        # {
        #     "label": _("Reserved Qty (Sales Orders)"),
        #     "fieldname": "reserved_qty_sales_orders",
        #     "fieldtype": "Float",
        #     "width": 180
        # },
        {
            "label": _("Available Qty"),
            "fieldname": "available_qty",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Projected Qty (ERPNext)"),
            "fieldname": "projected_qty_erpnext",
            "fieldtype": "Float",
            "width": 150,
            "description": _("Standard ERPNext projected quantity for reference (if applicable)")
        }
    ]

def get_data(filters):
    data = []
    
    company = filters.get("company")
    from_date = getdate(filters.get("from_date", nowdate())) # Not directly used for current stock, but for future reservations
    to_date = getdate(filters.get("to_date")) # Used to check reservations up to this date
    
    item_conditions = ""
    # warehouse_conditions = "" # Not used directly in item_query, but in sub-queries
    sql_params = {"company": company, "to_date": to_date, "from_date": from_date} # Added from_date

    if filters.get("item_code"):
        item_conditions += " AND i.name = %(item_code)s" # Corrected to i.name for item_code
        sql_params["item_code"] = filters.get("item_code")
    if filters.get("item_group"):
        item_conditions += " AND i.item_group = %(item_group)s"
        sql_params["item_group"] = filters.get("item_group")
    
    # Get all rental items
    items_query = f"""
        SELECT 
            i.name as item_code, 
            i.item_name, 
            i.item_group
        FROM `tabItem` i
        WHERE i.is_rental_item = 1 
          AND i.disabled = 0
          {item_conditions}
    """
    rental_items = frappe.db.sql(items_query, sql_params, as_dict=True)

    for item in rental_items:
        actual_qty_filters = {"item_code": item.item_code}
        warehouse_filter_value = filters.get("warehouse")
        if warehouse_filter_value:
            actual_qty_filters["warehouse"] = warehouse_filter_value
        
        actual_qty = frappe.db.get_value("Bin", actual_qty_filters, "sum(actual_qty)") or 0
        
        # Reserved Qty from Rental Jobs
        reserved_sql_params = {
            "item_code": item.item_code,
            "company": company,
            "to_date": to_date,
            "from_date": from_date # from_date is important to consider jobs starting in future but reserving now
        }
        warehouse_job_filter_sql = ""
        if warehouse_filter_value:
            # This assumes Rental Job has a 'set_warehouse' field. Adjust if different.
            warehouse_job_filter_sql = " AND rj.set_warehouse = %(warehouse)s"
            reserved_sql_params["warehouse"] = warehouse_filter_value

        reserved_qty_rental_jobs_result = frappe.db.sql(f"""
            SELECT SUM(rji.qty) 
            FROM `tabRental Job Item` rji
            JOIN `tabRental Job` rj ON rji.parent = rj.name
            WHERE rji.item_code = %(item_code)s
              AND rj.docstatus = 1
              AND rj.status IN ('Order Confirmed', 'Ready for Dispatch', 'Dispatched', 'In Use')
              AND rj.company = %(company)s
              AND rj.scheduled_dispatch_date <= %(to_date)s 
              AND rj.scheduled_return_date >= %(from_date)s 
              {warehouse_job_filter_sql}
        """, reserved_sql_params)
        
        reserved_qty_rj = flt(reserved_qty_rental_jobs_result[0][0] if reserved_qty_rental_jobs_result and reserved_qty_rental_jobs_result[0] else 0)

        available_qty = actual_qty - reserved_qty_rj

        projected_qty_erpnext = 0
        try:
            from erpnext.stock.utils import get_projected_qty as get_erpnext_projected_qty
            warehouse_for_proj = warehouse_filter_value or frappe.db.get_single_value("Stock Settings", "default_warehouse")
            if warehouse_for_proj:
                projected_qty_erpnext = get_erpnext_projected_qty(item.item_code, warehouse_for_proj, to_date) # Use to_date for projection
        except ImportError:
            pass 
        except Exception as e:
            frappe.log_error(f"Could not get projected_qty for {item.item_code}: {e}", "ReservedVsAvailableStockReport")

        data.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "warehouse": warehouse_filter_value or _("All Warehouses"),
            "actual_qty": actual_qty,
            "reserved_qty_rental_jobs": reserved_qty_rj,
            "available_qty": available_qty,
            "projected_qty_erpnext": projected_qty_erpnext
        })
        
    return data
