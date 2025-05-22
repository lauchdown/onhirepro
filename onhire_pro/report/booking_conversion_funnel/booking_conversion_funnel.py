# Project/onhire_pro/onhire_pro/report/booking_conversion_funnel/booking_conversion_funnel.py
import frappe
from frappe import _
from frappe.utils import getdate, flt, add_days

def execute(filters=None):
    columns = get_columns(filters)
    data, chart_data = get_data(filters)
    
    chart = None
    if chart_data:
        chart = {
            "type": "bar", # Or 'funnel' if a suitable library/method is available
            "data": {
                'labels': [d['stage'] for d in chart_data],
                'datasets': [{
                    'name': _("Count"),
                    'values': [d['count'] for d in chart_data]
                }]
            },
            "title": _("Booking Conversion Funnel")
        }
        # For a true funnel chart, specific JS library might be needed in report's JS file.
        # Frappe charts might not have a direct funnel type. A bar chart can represent stages.

    return columns, data, None, chart, None # No report summary for this one

def get_columns(filters):
    return [
        {"label": _("Funnel Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 250},
        {"label": _("Count"), "fieldname": "count", "fieldtype": "Int", "width": 150},
        {"label": _("Conversion Rate (%)"), "fieldname": "conversion_rate", "fieldtype": "Percent", "width": 180, "description": _("Conversion from previous stage")}
    ]

def get_data(filters):
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    sales_person = filters.get("sales_person")
    territory = filters.get("territory")

    base_filters = {
        "docstatus": 1, 
        "company": company,
    }
    # Date filter applies to the creation/transaction date of the initial document (Quotation)
    if from_date and to_date:
        base_filters["transaction_date"] = ["between", [from_date, to_date]]
    elif from_date:
        base_filters["transaction_date"] = [">=", from_date]
    elif to_date:
        base_filters["transaction_date"] = ["<=", to_date]


    if sales_person:
        base_filters["owner"] = sales_person 
    if territory:
        base_filters["territory"] = territory


    # Stage 1: Quotations Created (Rental Type)
    quotation_filters = base_filters.copy()
    quotation_filters["custom_is_rental_request"] = 1 
    
    quotations_created_count = frappe.db.count("Quotation", quotation_filters)

    # Stage 2: Quotations Sent / Active (using status)
    quotations_sent_filters = quotation_filters.copy()
    # Define what status means "sent" or "active enough to be considered in funnel"
    quotations_sent_filters["status"] = ["not in", ["Draft", "Cancelled", "Expired", "Lost"]] 
    quotations_sent_count = frappe.db.count("Quotation", quotations_sent_filters)


    # Stage 3: Orders Created (from these Quotations)
    # This counts quotations that have reached a status indicating an order was made.
    sales_orders_filters = quotation_filters.copy()
    sales_orders_filters["status"] = ["in", ["Order Confirmed", "Order Created", "Sales Order"]] # Adjust statuses as per workflow
    sales_orders_created_count = frappe.db.count("Quotation", sales_orders_filters)


    # Stage 4: Rental Jobs Created (linked to the initial Quotations)
    # This requires a link from Rental Job back to Quotation.
    # Assuming Rental Job has a field 'quotation' (or 'prevdoc_docname' if made via Sales Order from Quotation)
    rental_jobs_created_count = 0
    if frappe.db.has_column("Rental Job", "quotation"): # Check if direct link exists
        rj_q_filters = {
            "rj.docstatus": 1, "rj.company": company,
            "q.name": ["in", [d.name for d in frappe.get_all("Quotation", filters=quotation_filters, fields=["name"])]]
             # This subquery can be large. Better to filter Rental Jobs by date range too.
        }
        # Add date filter for Rental Job creation if needed, e.g., within X days of quotation.
        # For simplicity, linking directly to the filtered quotations.
        
        # This query structure is conceptual for joining.
        # A more performant way might be to get all relevant quotations first, then check which have linked jobs.
        relevant_quotation_names = [d.name for d in frappe.get_all("Quotation", filters=quotation_filters, fields=["name"])]
        if relevant_quotation_names:
            rental_jobs_created_count = frappe.db.count("Rental Job", {"quotation": ["in", relevant_quotation_names], "docstatus": 1, "company": company})
        else:
            rental_jobs_created_count = 0
    else:
        frappe.log_info("Rental Job to Quotation link ('quotation' field) not found for accurate funnel Stage 4.", "BookingConversionFunnel")


    # Stage 5: Rental Jobs Completed (from the created Rental Jobs)
    rental_jobs_completed_count = 0
    if rental_jobs_created_count > 0 and frappe.db.has_column("Rental Job", "quotation"): # Only if jobs were found and link exists
        # This counts jobs linked to the initial set of quotations that are now 'Completed'.
        if relevant_quotation_names: # from previous stage
            rental_jobs_completed_count = frappe.db.count("Rental Job", {
                "quotation": ["in", relevant_quotation_names], 
                "status": "Completed", 
                "docstatus": 1,
                "company": company
            })
    else:
         if not frappe.db.has_column("Rental Job", "quotation"):
            frappe.log_info("Rental Job to Quotation link ('quotation' field) not found for accurate funnel Stage 5.", "BookingConversionFunnel")


    funnel_data = [
        {"stage": _("1. Quotations Created (Rental)"), "count": quotations_created_count, "conversion_rate": 100.0},
        {"stage": _("2. Quotations Active/Sent"), "count": quotations_sent_count, "conversion_rate": 0.0},
        {"stage": _("3. Orders Confirmed (from Quotes)"), "count": sales_orders_created_count, "conversion_rate": 0.0},
        {"stage": _("4. Rental Jobs Created (from Quotes)"), "count": rental_jobs_created_count, "conversion_rate": 0.0},
        {"stage": _("5. Rental Jobs Completed"), "count": rental_jobs_completed_count, "conversion_rate": 0.0}
    ]

    for i in range(1, len(funnel_data)):
        prev_count = funnel_data[i-1]["count"]
        current_count = funnel_data[i]["count"]
        if prev_count > 0:
            funnel_data[i]["conversion_rate"] = round((current_count / prev_count) * 100, 2)
        else:
            funnel_data[i]["conversion_rate"] = 0.0 if current_count == 0 else 100.0 # If prev is 0 but current is >0 (unlikely in funnel)
            
    chart_data_for_funnel = [{"stage": d["stage"], "count": d["count"]} for d in funnel_data]

    return funnel_data, chart_data_for_funnel
