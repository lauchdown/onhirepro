# Project/onhire_pro/onhire_pro/report/customer_lifetime_value_rental/customer_lifetime_value_rental.py
import frappe
from frappe import _
from frappe.utils import getdate, flt

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
        {"label": _("First Rental Date"), "fieldname": "first_rental_date", "fieldtype": "Date", "width": 150},
        {"label": _("Last Rental Date"), "fieldname": "last_rental_date", "fieldtype": "Date", "width": 150},
        {"label": _("Total Rental Jobs"), "fieldname": "total_rental_jobs", "fieldtype": "Int", "width": 150},
        {"label": _("Total Rental Revenue (CLV)"), "fieldname": "total_rental_revenue", "fieldtype": "Currency", "width": 200}
    ]

def get_data(filters):
    sql_conditions = ["si.docstatus = 1", "si.company = %(company)s"]
    sql_params = {"company": filters.get("company")}

    customer_join_condition = "JOIN `tabCustomer` c ON si.customer = c.name"
    customer_conditions_list = [] # Use a list to build customer conditions

    if filters.get("customer_group"):
        customer_conditions_list.append("c.customer_group = %(customer_group)s")
        sql_params["customer_group"] = filters.get("customer_group")
    
    if filters.get("from_acquisition_date"):
        customer_conditions_list.append("c.creation >= %(from_acq_date)s")
        sql_params["from_acq_date"] = filters.get("from_acquisition_date")
    if filters.get("to_acquisition_date"):
        customer_conditions_list.append("c.creation <= %(to_acq_date)s")
        sql_params["to_acq_date"] = filters.get("to_acquisition_date")

    if customer_conditions_list: # If there are any customer specific conditions
        sql_conditions.append("(" + " AND ".join(customer_conditions_list) + ")")


    sql_conditions.append("si.custom_linked_rental_job IS NOT NULL")

    query = f"""
        SELECT
            si.customer,
            c.customer_name,
            MIN(rj.scheduled_dispatch_date) as first_rental_date,
            MAX(rj.scheduled_return_date) as last_rental_date, 
            COUNT(DISTINCT si.custom_linked_rental_job) as total_rental_jobs,
            SUM(sii.base_net_amount) as total_rental_revenue
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name
        {customer_join_condition}
        LEFT JOIN `tabRental Job` rj ON si.custom_linked_rental_job = rj.name 
            AND rj.docstatus = 1 
            AND rj.company = si.company 
        WHERE {" AND ".join(sql_conditions)}
        GROUP BY si.customer, c.customer_name
        ORDER BY total_rental_revenue DESC
    """
    
    data = frappe.db.sql(query, sql_params, as_dict=True)
    return data
