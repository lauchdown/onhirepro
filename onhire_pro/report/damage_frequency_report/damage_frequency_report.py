# Project/onhire_pro/onhire_pro/report/damage_frequency_report/damage_frequency_report.py
import frappe
from frappe import _
from frappe.utils import getdate, flt, cint

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": _("Serial No"), "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial No", "width": 140},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 120},
        {"label": _("Number of Rentals in Period"), "fieldname": "number_of_rentals", "fieldtype": "Int", "width": 180},
        {"label": _("Number of Damage Incidents"), "fieldname": "damage_incidents", "fieldtype": "Int", "width": 180},
        {"label": _("Damage Rate (%)"), "fieldname": "damage_rate", "fieldtype": "Percent", "width": 130}
    ]

def get_data(filters):
    sql_params = {
        "company": filters.get("company"),
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date")
    }
    
    conditions_str = "rj.company = %(company)s AND rj.docstatus = 1 AND rj.actual_return_date IS NOT NULL AND rj.scheduled_return_date IS NOT NULL AND rj.status IN ('Items Returned', 'Completed', 'Inspection Pending', 'Invoice Pending', 'Invoiced')"
    
    if filters.get("from_date"):
        conditions_str += " AND rj.actual_return_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions_str += " AND rj.actual_return_date <= %(to_date)s"
    
    if filters.get("item_code"):
        conditions_str += " AND rji.item_code = %(item_code)s"
        sql_params["item_code"] = filters.get("item_code")
    if filters.get("item_group"):
        conditions_str += " AND i.item_group = %(item_group)s"
        sql_params["item_group"] = filters.get("item_group")
    if filters.get("serial_no"):
        conditions_str += " AND rji.serial_no = %(serial_no)s"
        sql_params["serial_no"] = filters.get("serial_no")

    # Check if custom_item_damaged field exists for fallback
    has_custom_item_damaged_field = frappe.db.has_column("Rental Job Item", "custom_item_damaged")
    damage_case_expression = "CASE WHEN ca.overall_condition_rating IN ('Damaged', 'Needs Repair') THEN 1 "
    if has_custom_item_damaged_field:
        damage_case_expression += "WHEN rji.custom_item_damaged = 1 THEN 1 ELSE 0 END"
    else:
        damage_case_expression += "ELSE 0 END"


    query = f"""
        SELECT
            rji.item_code,
            i.item_name,
            rji.serial_no,
            i.item_group,
            COUNT(DISTINCT rji.parent) as number_of_rentals,
            SUM({damage_case_expression}) as damage_incidents
        FROM `tabRental Job Item` rji
        JOIN `tabRental Job` rj ON rji.parent = rj.name
        JOIN `tabItem` i ON rji.item_code = i.name
        LEFT JOIN `tabCondition Assessment` ca ON ca.rental_job_item = rji.name 
            AND ca.assessment_type = 'Post-Rental' 
            AND ca.docstatus = 1
        WHERE {conditions_str}
        GROUP BY rji.item_code, i.item_name, rji.serial_no, i.item_group
        ORDER BY damage_incidents DESC, rji.item_code, rji.serial_no
    """
    
    data = frappe.db.sql(query, sql_params, as_dict=True)

    for row in data:
        if row.number_of_rentals and flt(row.number_of_rentals) > 0:
            row.damage_rate = (flt(row.damage_incidents) / flt(row.number_of_rentals)) * 100
        else:
            row.damage_rate = 0.0
            
    return data
