// Project/onhire_pro/onhire_pro/report/rental_revenue_report/rental_revenue_report.js
frappe.query_reports["Rental Revenue Report"] = {
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
            "default": frappe.datetime.get_fiscal_year_start(frappe.datetime.now_date()), // Default to fiscal year start
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
            "fieldname": "periodicity",
            "label": __("Periodicity"),
            "fieldtype": "Select",
            "options": "Monthly\nQuarterly\nYearly\nDaily\nWeekly", // Added Daily/Weekly
            "default": "Monthly"
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
        },
        {
            "fieldname": "sales_person",
            "label": __("Sales Person"),
            "fieldtype": "Link",
            "options": "Sales Person"
            // Assuming Sales Invoice or linked Rental Job has 'sales_person'
        },
        {
            "fieldname": "group_by",
            "label": __("Group By"),
            "fieldtype": "Select",
            "options": "\nItem Group\nCustomer\nSales Person\nItem Code" // Added Item Code
        }
    ],
    "formatter": function(value, row, column, data, report) {
        if (column.df.fieldname === "revenue_change_percentage" || column.df.fieldname === "growth_percentage") {
            if (value > 0) {
                return `<span style='color:green;'>${value}%</span>`;
            } else if (value < 0) {
                return `<span style='color:red;'>${value}%</span>`;
            }
        }
        return value;
    }
};
