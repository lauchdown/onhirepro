// Project/onhire_pro/onhire_pro/report/customer_lifetime_value_rental/customer_lifetime_value_rental.js
frappe.query_reports["Customer Lifetime Value (Rental)"] = {
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
            "fieldname": "customer_group",
            "label": __("Customer Group"),
            "fieldtype": "Link",
            "options": "Customer Group"
        },
        {
            "fieldname": "from_acquisition_date",
            "label": __("From Acquisition Date (Customer Creation)"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_acquisition_date",
            "label": __("To Acquisition Date (Customer Creation)"),
            "fieldtype": "Date"
        }
        // Add a filter for specific customer if needed
        // {
        //     "fieldname": "customer",
        //     "label": __("Customer"),
        //     "fieldtype": "Link",
        //     "options": "Customer"
        // }
    ]
};
