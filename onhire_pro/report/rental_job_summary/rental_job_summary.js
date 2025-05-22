// Project/onhire_pro/onhire_pro/report/rental_job_summary/rental_job_summary.js
frappe.query_reports["Rental Job Summary"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date (Dispatch Date)"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.now_date(), -1),
        },
        {
            "fieldname": "to_date",
            "label": __("To Date (Dispatch Date)"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
        },
        {
            "fieldname": "customer",
            "label": __("Customer"),
            "fieldtype": "Link",
            "options": "Customer"
        },
        {
            "fieldname": "status",
            "label": __("Job Status"),
            "fieldtype": "Select",
            // These statuses should match the ones in Rental Job DocType
            "options": "\nDraft\nQuotation\nOrder Confirmed\nReady for Dispatch\nDispatched\nItems Returned\nInspection Pending\nInvoice Pending\nInvoiced\nCompleted\nCancelled\nOn Hold"
        },
        {
            "fieldname": "sales_person",
            "label": __("Sales Person"),
            "fieldtype": "Link",
            "options": "Sales Person" 
            // Assuming Rental Job has a 'sales_person' field or can be linked via Customer/Quotation
        }
    ]
};
