# Project/onhire_pro/onhire_pro/report/rental_job_summary/rental_job_summary.py
import frappe
from frappe import _
from frappe.utils import getdate, flt, cstr

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Job ID"), "fieldname": "name", "fieldtype": "Link", "options": "Rental Job", "width": 120},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": _("Project Name"), "fieldname": "project_name", "fieldtype": "Data", "width": 150},
        {"label": _("Dispatch Date"), "fieldname": "scheduled_dispatch_date", "fieldtype": "Date", "width": 120},
        {"label": _("Return Date"), "fieldname": "scheduled_return_date", "fieldtype": "Date", "width": 120},
        {"label": _("Actual Return Date"), "fieldname": "actual_return_date", "fieldtype": "Date", "width": 130},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": _("Total Value"), "fieldname": "grand_total", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "hidden": 1},
        {"label": _("Items (Qty)"), "fieldname": "items_summary", "fieldtype": "Small Text", "width": 250},
        {"label": _("Notes"), "fieldname": "notes", "fieldtype": "Text", "width": 200}
        # Add Sales Person if available and filtered
    ]

def get_data(filters):
    sql_filters = {"docstatus": 1}
    # sql_params = {} # Not directly used with frappe.get_all filters like this

    if filters.get("company"):
        sql_filters["company"] = filters.get("company")
    
    # Date filtering logic
    date_filters = []
    if filters.get("from_date"):
        date_filters.append(["scheduled_dispatch_date", ">=", filters.get("from_date")])
    if filters.get("to_date"):
        date_filters.append(["scheduled_dispatch_date", "<=", filters.get("to_date")])
    
    if date_filters:
        # If only one date filter, it's simple. If both, frappe.get_all handles it as AND.
        # For a BETWEEN like experience on a single field, this structure is fine.
        for df in date_filters:
            if sql_filters.get(df[0]) and isinstance(sql_filters[df[0]], list):
                 # This part of logic for combining date filters might be tricky with get_all
                 # It's often simpler to construct a single ["between", [from, to]] if both present
                 pass # Let's simplify date filtering for get_all
            else:
                sql_filters[df[0]] = [df[1], df[2]]

    # Simplified date filter handling for get_all:
    if filters.get("from_date") and filters.get("to_date"):
        sql_filters["scheduled_dispatch_date"] = ["between", [filters.get("from_date"), filters.get("to_date")]]
    elif filters.get("from_date"):
        sql_filters["scheduled_dispatch_date"] = [">=", filters.get("from_date")]
    elif filters.get("to_date"):
        sql_filters["scheduled_dispatch_date"] = ["<=", filters.get("to_date")]


    if filters.get("customer"):
        sql_filters["customer"] = filters.get("customer")
    if filters.get("status"):
        sql_filters["status"] = filters.get("status")
    if filters.get("sales_person"):
        if frappe.db.has_column("Rental Job", "sales_person"):
             sql_filters["sales_person"] = filters.get("sales_person")
        # else:
            # frappe.msgprint(_("Filtering by Sales Person is not fully supported if 'sales_person' field is not on Rental Job."), indicator="orange")


    fields = ["name", "customer", "project_name", "scheduled_dispatch_date", "scheduled_return_date", 
              "actual_return_date", "status", "grand_total", "currency", "notes", "company"] # Added company for currency fallback
    
    rental_jobs = frappe.get_all("Rental Job", filters=sql_filters, fields=fields, order_by="scheduled_dispatch_date desc")

    for job in rental_jobs:
        job_items = frappe.get_all("Rental Job Item", 
                                   filters={"parent": job.name}, 
                                   fields=["item_name", "qty", "item_code"])
        items_summary_parts = []
        for item in job_items:
            items_summary_parts.append(f"{item.item_name or item.item_code} ({flt(item.qty)})")
        job["items_summary"] = ", ".join(items_summary_parts) if items_summary_parts else _("No items")
        
        if not job.currency and job.grand_total: # Ensure currency for formatting
            job_company = job.company or filters.get("company") # Get company from job or filter
            if job_company:
                 job.currency = frappe.get_cached_value("Company", job_company, "default_currency")
            if not job.currency: # Fallback if still no currency
                 job.currency = frappe.get_cached_value("Global Defaults", None, "default_currency")


    return rental_jobs
