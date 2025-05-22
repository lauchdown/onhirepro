# Project/onhire_pro/onhire_pro/report/revenue_by_item_category/revenue_by_item_category.py
import frappe
from frappe import _
from frappe.utils import getdate, flt, date_diff

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 150},
        {"label": _("Total Rental Duration (Days)"), "fieldname": "total_rental_duration", "fieldtype": "Float", "width": 180},
        {"label": _("Number of Rentals"), "fieldname": "number_of_rentals", "fieldtype": "Int", "width": 140},
        {"label": _("Total Revenue"), "fieldname": "total_revenue", "fieldtype": "Currency", "width": 150},
        {"label": _("Average Revenue per Rental"), "fieldname": "avg_revenue_per_rental", "fieldtype": "Currency", "width": 200}
    ]

def get_data(filters):
    sql_params = {
        "company": filters.get("company"),
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date")
    }
    
    conditions = ["si.docstatus = 1", "si.company = %(company)s", "si.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
    conditions.append("si.custom_linked_rental_job IS NOT NULL") 

    if filters.get("item_code"):
        conditions.append("sii.item_code = %(item_code)s")
        sql_params["item_code"] = filters.get("item_code")
    if filters.get("item_group"):
        conditions.append("item.item_group = %(item_group)s") 
        sql_params["item_group"] = filters.get("item_group")
    
    
    query = f"""
        SELECT
            sii.item_code,
            sii.item_name,
            item.item_group,
            SUM(sii.base_net_amount) as total_revenue,
            COUNT(DISTINCT si.custom_linked_rental_job) as number_of_rentals
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name
        JOIN `tabItem` item ON sii.item_code = item.name
        WHERE {" AND ".join(conditions)}
        GROUP BY sii.item_code, sii.item_name, item.item_group
        ORDER BY total_revenue DESC
    """
    
    data = frappe.db.sql(query, sql_params, as_dict=True)

    for row in data:
        duration_sql_params = {
            "item_code": row.item_code, "company": filters.get("company"),
            "from_date": filters.get("from_date"), "to_date": filters.get("to_date")
        }
        # Fetch distinct rental jobs for this item that have invoices in the period
        linked_jobs_query = f"""
            SELECT DISTINCT si.custom_linked_rental_job
            FROM `tabSales Invoice Item` sii
            JOIN `tabSales Invoice` si ON sii.parent = si.name
            WHERE sii.item_code = %(item_code)s
              AND si.docstatus = 1
              AND si.company = %(company)s
              AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
              AND si.custom_linked_rental_job IS NOT NULL
        """
        linked_jobs_res = frappe.db.sql(linked_jobs_query, {"item_code": row.item_code, "company": filters.get("company"), "from_date": filters.get("from_date"), "to_date": filters.get("to_date")})
        linked_job_names = [j[0] for j in linked_jobs_res if j[0]]

        total_item_duration = 0
        if linked_job_names:
            duration_data = frappe.db.sql("""
                SELECT SUM(DATEDIFF(LEAST(rj.scheduled_return_date, %(to_date)s), GREATEST(rj.scheduled_dispatch_date, %(from_date)s)) + 1)
                FROM `tabRental Job Item` rji
                JOIN `tabRental Job` rj ON rji.parent = rj.name
                WHERE rji.item_code = %(item_code)s 
                  AND rj.name IN %(linked_jobs)s
                  AND rj.docstatus = 1
                  AND rj.scheduled_dispatch_date <= %(to_date)s 
                  AND rj.scheduled_return_date >= %(from_date)s
            """, {"item_code": row.item_code, "to_date": filters.get("to_date"), "from_date": filters.get("from_date"), "linked_jobs": tuple(linked_job_names)})
            row.total_rental_duration = flt(duration_data[0][0] if duration_data and duration_data[0] else 0)
        else:
            row.total_rental_duration = 0


        if row.number_of_rentals and flt(row.number_of_rentals) > 0:
            row.avg_revenue_per_rental = flt(row.total_revenue) / flt(row.number_of_rentals)
        else:
            row.avg_revenue_per_rental = 0.0
            
    return data
