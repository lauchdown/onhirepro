frappe.pages['dashboard'].on_page_load = function(wrapper) { // Assuming route is 'dashboard'
    frappe.customer_dashboard_view = new CustomerDashboardView(wrapper);
}

class CustomerDashboardView {
    constructor(wrapper) {
        this.wrapper = $(wrapper);
        this.page = wrapper.page;
        this.stats = {};
        this.alerts = [];
        this.make();
    }

    make() {
        this.setup_page_head();
        this.setup_layout();
        this.load_dashboard_data();
    }

    setup_page_head() {
        this.page.set_title(__("My Dashboard"));
        // Primary action could be "New Booking Request"
        this.page.set_primary_action(__("New Rental Request"), () => {
            frappe.set_route("rental-booking-request");
        }, "add");
    }

    setup_layout() {
        // Main layout: Quick Links, Alerts, Key Metrics, Charts
        let layout_html = `
            <div class="customer-dashboard-container">
                <!-- Quick Links -->
                <div class="row section-divider">
                    <div class="col-md-12">
                        <h4>${__("Quick Actions")}</h4>
                        <p>
                            <a href="/app/rental-catalog" class="btn btn-default">${__("Browse Catalog")}</a>
                            <a href="/app/my-rentals" class="btn btn-default">${__("View My Rentals")}</a>
                            <a href="/app/my-documents" class="btn btn-default">${__("View My Documents")}</a>
                            <a href="/app/my-profile" class="btn btn-default">${__("Update My Profile")}</a>
                        </p>
                    </div>
                </div>

                <!-- Alerts Widget/Banner (CP_RENTAL.6.3) -->
                <div id="portal-alerts-widget" class="row section-divider" style="display:none;">
                    <div class="col-md-12">
                        <h4>${__("Notifications & Alerts")}</h4>
                        <div class="alert-list"></div>
                    </div>
                </div>
                
                <!-- Key Metrics (CP_RENTAL.11.1) -->
                <div class="row section-divider">
                    <div class="col-md-12"><h4>${__("Overview")}</h4></div>
                    <div class="col-md-3 col-xs-6">
                        <div class="dashboard-stat card-stat" id="stat-active-rentals">
                            <span class="stat-value">0</span><br>
                            <span class="stat-label">${__("Active Rentals")}</span>
                        </div>
                    </div>
                    <div class="col-md-3 col-xs-6">
                        <div class="dashboard-stat card-stat" id="stat-upcoming-returns">
                            <span class="stat-value">0</span><br>
                            <span class="stat-label">${__("Upcoming Returns (7 days)")}</span>
                        </div>
                    </div>
                    <div class="col-md-3 col-xs-6">
                        <div class="dashboard-stat card-stat" id="stat-total-spend">
                            <span class="stat-value">0</span><br>
                            <span class="stat-label">${__("Total Rental Spend (YTD)")}</span>
                        </div>
                    </div>
                    <div class="col-md-3 col-xs-6">
                        <div class="dashboard-stat card-stat" id="stat-avg-duration">
                            <span class="stat-value">0 days</span><br>
                            <span class="stat-label">${__("Avg. Rental Duration")}</span>
                        </div>
                    </div>
                </div>

                <!-- Dashboard Tiles (from Patch - CP_RENTAL.11.1) -->
                 <div class="row section-divider">
                     <div class="col-md-12"><h4>${__("Pending Actions")}</h4></div>
                     <div class="col-md-4 col-xs-12">
                        <div class="dashboard-tile card-stat" id="tile-pending-sor">
                            <span class="tile-value">0</span>
                            <span class="tile-label">${__("Pending SOR Returns")}</span>
                            <a href="/app/my-rentals?status=Active" class="tile-link">${__("View Details")} &rarr;</a>
                        </div>
                    </div>
                     <div class="col-md-4 col-xs-12">
                        <div class="dashboard-tile card-stat" id="tile-damage-review">
                            <span class="tile-value">0</span>
                            <span class="tile-label">${__("Damage Charges Under Review")}</span>
                             <a href="/app/my-documents" class="tile-link">${__("View Invoices")} &rarr;</a>
                        </div>
                    </div>
                    <!-- Add more tiles as needed -->
                </div>


                <!-- Chart Visualizations (CP_RENTAL.11.2) -->
                <div class="row section-divider">
                    <div class="col-md-12"><h4>${__("Rental Analytics")}</h4></div>
                    <div class="col-md-6">
                        <div class="chart-container card-stat">
                            <h5>${__("Monthly Rental Expenditure (Last 6 Months)")}</h5>
                            <div id="monthly-spend-chart"></div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="chart-container card-stat">
                             <h5>${__("Rentals by Item Category (Top 5)")}</h5>
                            <div id="category-distribution-chart"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        this.wrapper.find(".page-content").html(layout_html);
    }

    load_dashboard_data() {
        frappe.show_progress(__("Loading Dashboard..."), true, false);
        frappe.call({
            method: "onhire_pro.onhire_pro.customer_portal.utils.get_customer_dashboard_data", // New util function
            callback: (r) => {
                frappe.hide_progress();
                if (r.message) {
                    this.stats = r.message.stats || {};
                    this.alerts = r.message.alerts || [];
                    this.update_stats_display();
                    this.update_alerts_display();
                    this.render_charts(r.message.charts_data || {});
                } else {
                    frappe.msgprint({title: __("Error"), message: __("Could not load dashboard data."), indicator: "red"});
                }
            },
            error: (r) => {
                frappe.hide_progress();
                frappe.msgprint({title: __("Error"), message: __("Failed to fetch dashboard data."), indicator: "red"});
            }
        });
    }

    update_stats_display() {
        $('#stat-active-rentals .stat-value').text(this.stats.active_rentals || 0);
        $('#stat-upcoming-returns .stat-value').text(this.stats.upcoming_returns || 0);
        $('#stat-total-spend .stat-value').text(frappe.format_currency(this.stats.total_spend_ytd || 0, this.stats.currency));
        $('#stat-avg-duration .stat-value').text(`${this.stats.avg_rental_duration || 0} days`);
        
        $('#tile-pending-sor .tile-value').text(this.stats.pending_sor_returns || 0);
        $('#tile-damage-review .tile-value').text(this.stats.damage_charges_review || 0);
    }

    update_alerts_display() {
        const alerts_container = this.wrapper.find("#portal-alerts-widget .alert-list");
        alerts_container.empty();
        if (this.alerts.length > 0) {
            this.wrapper.find("#portal-alerts-widget").show();
            let alerts_html = '<ul class="list-group">';
            this.alerts.forEach(alert => {
                // Assuming alert object has: subject, message, link, type (e.g. 'info', 'warning', 'danger')
                alerts_html += `
                    <li class="list-group-item list-group-item-${alert.type || 'info'}">
                        <strong>${alert.subject}</strong>: ${alert.message}
                        ${alert.link ? `<a href="${alert.link}" class="btn btn-xs btn-default pull-right">${__("View")}</a>` : ''}
                    </li>`;
            });
            alerts_html += '</ul>';
            alerts_container.html(alerts_html);
        } else {
             this.wrapper.find("#portal-alerts-widget").hide();
        }
    }

    render_charts(charts_data) {
        // Monthly Spend Chart (CP_RENTAL.11.2)
        if (charts_data.monthly_spend && charts_data.monthly_spend.labels && charts_data.monthly_spend.values) {
            new frappe.Chart("#monthly-spend-chart", {
                title: __("Monthly Rental Spend"),
                data: {
                    labels: charts_data.monthly_spend.labels, // e.g., ["Jan", "Feb", ...]
                    datasets: [{
                        name: __("Spend"),
                        values: charts_data.monthly_spend.values // e.g., [100, 200, ...]
                    }]
                },
                type: 'bar', // 'bar', 'line', 'pie', 'percentage'
                height: 250,
                colors: ['#7cd6fd'],
                truncateLegends: true,
                tooltipOptions: {
                    formatTooltipY: d => frappe.format_currency(d, this.stats.currency)
                }
            });
        } else {
             $("#monthly-spend-chart").html(`<p class="text-muted text-center">${__("No expenditure data to display.")}</p>`);
        }

        // Category Distribution Chart (CP_RENTAL.11.2)
        if (charts_data.category_distribution && charts_data.category_distribution.labels && charts_data.category_distribution.values) {
            new frappe.Chart("#category-distribution-chart", {
                title: __("Rentals by Category"),
                data: {
                    labels: charts_data.category_distribution.labels, // e.g., ["Category A", "Category B", ...]
                    datasets: [{
                        name: __("Count"),
                        values: charts_data.category_distribution.values // e.g., [10, 5, ...]
                    }]
                },
                type: 'pie',
                height: 250,
                truncateLegends: true
            });
        } else {
            $("#category-distribution-chart").html(`<p class="text-muted text-center">${__("No category data to display.")}</p>`);
        }
    }
}
