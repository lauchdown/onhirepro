// Project/onhire_pro/onhire_pro/report/sor_kept_vs_returned_ratio/sor_kept_vs_returned_ratio.js
frappe.query_reports["SOR Kept vs. Returned Ratio"] = {
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
            "label": __("From Date (Job Dispatch Date)"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.now_date(), -3),
        },
        {
            "fieldname": "to_date",
            "label": __("To Date (Job Dispatch Date)"),
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
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                return { filters: { "is_rental_item": 1 } }
            }
        },
        {
            "fieldname": "item_group",
            "label": __("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group"
        }
    ]
};
