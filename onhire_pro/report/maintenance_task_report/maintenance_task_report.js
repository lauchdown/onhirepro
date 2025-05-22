// Project/onhire_pro/onhire_pro/report/maintenance_task_report/maintenance_task_report.js
frappe.query_reports["Maintenance Task Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
            // "reqd": 1 // Make company optional if tasks can be non-company specific
        },
        {
            "fieldname": "from_date",
            "label": __("From Date (Task Start/Creation)"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.now_date(), -1),
        },
        {
            "fieldname": "to_date",
            "label": __("To Date (Task Start/Creation)"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            // These options should match the statuses in your Maintenance Task DocType
            "options": "\nOpen\nIn Progress\nOn Hold\nCompleted\nCancelled" 
        },
        {
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                return { filters: { "is_rental_item": 1 } } // Assuming maintenance is for rental items
            }
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
        },
        {
            "fieldname": "assigned_to",
            "label": __("Assigned To"),
            "fieldtype": "Link",
            "options": "User"
        },
        {
            "fieldname": "maintenance_type", // Assuming a field 'maintenance_type' on Maintenance Task
            "label": __("Task Type"),
            "fieldtype": "Link", // Or Select, depending on how types are defined
            "options": "Maintenance Type" // Assuming a DocType "Maintenance Type"
        }
    ]
};
