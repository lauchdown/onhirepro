# Project/onhire_pro/onhire_pro/report/sor_kept_vs_returned_ratio/sor_kept_vs_returned_ratio.py
import frappe
from frappe import _
from frappe.utils import getdate, flt

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 120},
        {"label": _("Total SOR Issued (Qty)"), "fieldname": "total_sor_issued", "fieldtype": "Float", "width": 150},
        {"label": _("Total Kept (Qty)"), "fieldname": "total_kept", "fieldtype": "Float", "width": 120},
        {"label": _("Total Returned (Qty)"), "fieldname": "total_returned", "fieldtype": "Float", "width": 140},
        {"label": _("Pending Decision (Qty)"), "fieldname": "total_pending", "fieldtype": "Float", "width": 160},
        {"label": _("Kept Ratio (%)"), "fieldname": "kept_ratio", "fieldtype": "Percent", "width": 120}
    ]

def get_data(filters):
    sql_conditions = []
    sql_params = {"company": filters.get("company")}
    
    sql_conditions.append("rj.company = %(company)s")
    sql_conditions.append("rj.docstatus = 1")
    sql_conditions.append("rji.custom_is_sor = 1") # Filter for SOR items

    if filters.get("from_date"):
        sql_conditions.append("rj.scheduled_dispatch_date >= %(from_date)s") # Based on when job started
        sql_params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        sql_conditions.append("rj.scheduled_dispatch_date <= %(to_date)s")
        sql_params["to_date"] = filters.get("to_date")
    
    if filters.get("customer"):
        sql_conditions.append("rj.customer = %(customer)s")
        sql_params["customer"] = filters.get("customer")
    
    item_specific_conditions = ""
    if filters.get("item_code"):
        item_specific_conditions += " AND rji.item_code = %(item_code)s"
        sql_params["item_code"] = filters.get("item_code")
    if filters.get("item_group"):
        item_specific_conditions += " AND i.item_group = %(item_group)s" # Assumes join with Item table 'i'
        sql_params["item_group"] = filters.get("item_group")

    query = f"""
        SELECT
            rji.item_code,
            i.item_name,
            i.item_group,
            SUM(rji.qty) as total_sor_issued,
            SUM(CASE WHEN rji.custom_sor_status = 'Kept' THEN rji.qty ELSE 0 END) as total_kept,
            SUM(CASE WHEN rji.custom_sor_status = 'Returned' THEN rji.qty ELSE 0 END) as total_returned,
            SUM(CASE WHEN rji.custom_sor_status = 'Pending' THEN rji.qty ELSE 0 END) as total_pending
        FROM `tabRental Job Item` rji
        JOIN `tabRental Job` rj ON rji.parent = rj.name
        JOIN `tabItem` i ON rji.item_code = i.name
        WHERE {" AND ".join(sql_conditions)} {item_specific_conditions}
        GROUP BY rji.item_code, i.item_name, i.item_group
        ORDER BY rji.item_code
    """
    
    data = frappe.db.sql(query, sql_params, as_dict=True)

    for row in data:
        if row.total_sor_issued and flt(row.total_sor_issued) > 0: # Check for None and ensure not zero
            row.kept_ratio = (flt(row.total_kept) / flt(row.total_sor_issued)) * 100
        else:
            row.kept_ratio = 0.0
            
    return data
