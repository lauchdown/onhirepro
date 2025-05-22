// Project/onhire_pro/onhire_pro/report/booking_conversion_funnel/booking_conversion_funnel.js
frappe.query_reports["Booking Conversion Funnel"] = {
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
            "label": __("From Date (Quotation Creation)"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.now_date(), -3),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date (Quotation Creation)"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
            "reqd": 1
        },
        {
            "fieldname": "sales_person",
            "label": __("Sales Person"),
            "fieldtype": "Link",
            "options": "Sales Person"
            // Assuming Quotation has a 'sales_person' field
        },
        {
            "fieldname": "territory",
            "label": __("Territory"),
            "fieldtype": "Link",
            "options": "Territory"
            // Assuming Quotation has a 'territory' field
        }
    ],
    "onload": function(report) {
        // Optional: Add a placeholder for chart if Python doesn't generate it directly
        // report.page.add_field({
        //     fieldname: 'funnel_chart_area',
        //     fieldtype: 'HTML',
        //     label: 'Funnel Visualization'
        // });
    }
    // Formatter can be used if chart data is passed separately to render with JS library
};
