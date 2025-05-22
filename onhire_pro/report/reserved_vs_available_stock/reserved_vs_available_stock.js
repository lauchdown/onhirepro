// Project/onhire_pro/onhire_pro/report/reserved_vs_available_stock/reserved_vs_available_stock.js
frappe.query_reports["Reserved vs Available Stock"] = {
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
            "label": __("From Date (for future availability)"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date()
        },
        {
            "fieldname": "to_date",
            "label": __("To Date (for future availability)"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_days(frappe.datetime.now_date(), 30)
        },
        {
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item"
        },
        {
            "fieldname": "item_group",
            "label": __("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group"
        },
        {
            "fieldname": "warehouse",
            "label": __("Warehouse"),
            "fieldtype": "Link",
            "options": "Warehouse",
            "get_query": function() {
                let company = frappe.query_report.get_filter_value('company');
                return {
                    filters: {
                        "company": company,
                        "is_group": 0
                    }
                }
            }
        }
    ]
};
