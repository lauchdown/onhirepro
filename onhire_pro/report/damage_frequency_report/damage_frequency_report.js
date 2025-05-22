// Project/onhire_pro/onhire_pro/report/damage_frequency_report/damage_frequency_report.js
frappe.query_reports["Damage Frequency by Item"] = {
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
            "label": __("From Date (Assessment/Job Date)"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.now_date(), -12), // Default to last 12 months
        },
        {
            "fieldname": "to_date",
            "label": __("To Date (Assessment/Job Date)"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
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
        },
        {
            "fieldname": "serial_no",
            "label": __("Serial Number"),
            "fieldtype": "Link",
            "options": "Serial No",
            "get_query": function() {
                let item_code = frappe.query_report.get_filter_value('item_code');
                if (item_code) {
                    return { filters: { "item_code": item_code } }
                }
                return {};
            }
        }
    ]
};
