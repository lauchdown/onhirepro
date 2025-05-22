# Project/onhire_pro/onhire_pro/report/late_return_patterns/late_return_patterns.py
import frappe
from frappe import _
from frappe.utils import getdate, date_diff, flt, cint

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Rental Job ID"), "fieldname": "rental_job", "fieldtype": "Link", "options": "Rental Job", "width": 120},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 120},
        {"label": _("Scheduled Return Date"), "fieldname": "scheduled_return_date", "fieldtype": "Date", "width": 150},
        {"label": _("Actual Return Date"), "fieldname": "actual_return_date", "fieldtype": "Date", "width": 150},
        {"label": _("Days Late"), "fieldname": "days_late", "fieldtype": "Int", "width": 100},
        {"label": _("Late Return Reason"), "fieldname": "late_return_reason", "fieldtype": "Small Text", "width": 200} 
        # Assuming 'late_return_reason' is a custom field on Rental Job or Rental Job Item
    ]

def get_data(filters):
    sql_conditions = []
    sql_params = {}

    sql_params["company"] = filters.get("company")
    sql_conditions.append("rj.company = %(company)s")
    sql_conditions.append("rj.docstatus = 1")
    sql_conditions.append("rj.actual_return_date IS NOT NULL") # Ensure item has been returned
    sql_conditions.append("rj.scheduled_return_date IS NOT NULL")
    sql_conditions.append("rj.actual_return_date > rj.scheduled_return_date") # Core condition for late returns

    if filters.get("from_date"):
        sql_conditions.append("rj.actual_return_date >= %(from_date)s")
        sql_params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        sql_conditions.append("rj.actual_return_date <= %(to_date)s")
        sql_params["to_date"] = filters.get("to_date")
    
    if filters.get("customer"):
        sql_conditions.append("rj.customer = %(customer)s")
        sql_params["customer"] = filters.get("customer")

    # Item Code and Item Group filters require joining with Rental Job Item and Item
    item_join_clause = "JOIN `tabRental Job Item` rji ON rj.name = rji.parent JOIN `tabItem` i ON rji.item_code = i.name"
    
    if filters.get("item_code"):
        sql_conditions.append("rji.item_code = %(item_code)s")
        sql_params["item_code"] = filters.get("item_code")
    
    if filters.get("item_group"):
        sql_conditions.append("i.item_group = %(item_group)s")
        sql_params["item_group"] = filters.get("item_group")
        
    min_days_late = cint(filters.get("min_days_late", 1))
    # Ensure min_days_late is positive to avoid issues with DATEDIFF if it's 0 or negative from filter
    if min_days_late < 0: min_days_late = 0 
    
    # DATEDIFF(rj.actual_return_date, rj.scheduled_return_date) will give the difference
    sql_conditions.append(f"DATEDIFF(rj.actual_return_date, rj.scheduled_return_date) >= {min_days_late}")


    query = f"""
        SELECT 
            rj.name as rental_job,
            rj.customer,
            rji.item_code,
            i.item_name,
            i.item_group,
            rj.scheduled_return_date,
            rj.actual_return_date,
            DATEDIFF(rj.actual_return_date, rj.scheduled_return_date) as days_late,
            rj.custom_late_return_reason as late_return_reason 
            -- Assuming 'custom_late_return_reason' is a custom field on Rental Job
        FROM `tabRental Job` rj
        {item_join_clause}
        WHERE {" AND ".join(sql_conditions)}
        ORDER BY days_late DESC, rj.actual_return_date DESC
    """
    
    data = frappe.db.sql(query, sql_params, as_dict=True)
    return data
