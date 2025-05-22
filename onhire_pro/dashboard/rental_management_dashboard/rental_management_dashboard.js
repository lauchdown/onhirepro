// Project/onhire_pro/onhire_pro/dashboard/rental_management_dashboard/rental_management_dashboard.js
frappe.provide("onhire_pro.RentalManagementDashboard");

onhire_pro.RentalManagementDashboard = {
    onload: function(wrapper) {
        this.wrapper = $(wrapper);
        this.page = wrapper.page;
        this.page.set_title(__("Rental Management Dashboard"));
        this.setup_views();
    },

    setup_views: function() {
        // Placeholder for setting up dashboard views and widgets
        // This would typically involve adding sections and rendering charts/number cards
        // based on the dashboard JSON definition and data from chart sources.

        // Placeholder for threshold highlighting logic
        this.apply_threshold_highlighting = function() {
            // This function fetches threshold values from Rental Settings
            // and applies CSS classes (e.g., kpi-critical, kpi-warning) to dashboard widgets
            // based on their current values.
            console.log("Applying threshold highlighting");

            frappe.call({
                method: "frappe.client.get_single",
                args: { doctype: "Rental Settings" },
                callback: function(r) {
                    if (r.message) {
                        let settings = r.message;
                        // Example: Apply highlighting to an "Overdue Returns" widget
                        // You would need to identify the specific HTML element for this widget
                        // and get its value. This is a simplified example.
                        let overdue_returns_widget = $(".dashboard-kpi-card[data-widget-name='Overdue Returns']"); // Assuming a data attribute for widget name
                        if (overdue_returns_widget.length) {
                            let overdue_count = parseFloat(overdue_returns_widget.find(".kpi-value").text()); // Assuming value is in an element with class kpi-value
                            if (!isNaN(overdue_count) && overdue_count >= settings.custom_overdue_returns_threshold_critical) {
                                overdue_returns_widget.addClass("kpi-critical");
                            } else {
                                overdue_returns_widget.removeClass("kpi-critical");
                            }
                        }

                        // Add similar logic for other KPIs with thresholds
                        // e.g., At Risk Stock, Overdue Invoice Amount
                    }
                }
            });
        };

        // Call threshold highlighting on load and potentially on data refresh
        this.apply_threshold_highlighting();
    }
};
