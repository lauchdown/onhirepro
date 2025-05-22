// Project/onhire_pro/onhire_pro/report/revenue_by_item_category/revenue_by_item_category.js
frappe.query_reports["Revenue by Item-Category"] = {
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
            "label": __("From Date (Invoice Posting Date)"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.now_date(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date (Invoice Posting Date)"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
            "reqd": 1
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
        // Add customer filter if needed
        // {
        //     "fieldname": "customer",
        //     "label": __("Customer"),
        //     "fieldtype": "Link",
        //     "options": "Customer"
        // }
    ]
};
