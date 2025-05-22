frappe.pages['my-rentals'].on_page_load = function(wrapper) {
    frappe.my_rentals_view = new MyRentalsView(wrapper);
}

class MyRentalsView {
    constructor(wrapper) {
        this.wrapper = $(wrapper);
        this.page = wrapper.page;
        this.filters = {
            status: null 
        };
        this.rental_jobs = [];
        this.make();
    }

    make() {
        this.setup_page_head();
        this.setup_filters_area();
        this.setup_rental_list_area();
        this.load_rental_jobs();
    }

    setup_page_head() {
        this.page.set_title(__("My Rentals"));
    }

    setup_filters_area() {
        // Statuses can be fetched from Rental Job doctype or defined here
        const rental_job_statuses = [
            "Draft", "Quotation", "Order Confirmed", "Ready for Dispatch", 
            "Dispatched", "Items Returned", "Inspection Pending", 
            "Invoice Pending", "Invoiced", "Completed", "Cancelled", "On Hold"
        ]; 

        let filters_html = `
            <div class="row my-rentals-filters" style="margin-bottom: 20px; padding: 15px; background-color: #f9f9f9; border-radius: 4px;">
                <div class="col-md-4">
                    <label for="rental_job_status_filter">${__("Filter by Status")}</label>
                    <select id="rental_job_status_filter" class="form-control">
                        <option value="">${__("All Statuses")}</option>
                        ${rental_job_statuses.map(s => `<option value="${s}">${s}</option>`).join('')}
                    </select>
                </div>
                 <div class="col-md-4">
                    <label>&nbsp;</label><br>
                    <button class="btn btn-primary btn-sm" id="apply_my_rentals_filters">${__("Apply")}</button>
                    <button class="btn btn-default btn-sm" id="clear_my_rentals_filters" style="margin-left: 5px;">${__("Clear")}</button>
                </div>
            </div>
        `;
        this.wrapper.find(".page-content").append(filters_html);

        $('#apply_my_rentals_filters').on('click', () => this.apply_filters());
        $('#clear_my_rentals_filters').on('click', () => this.clear_filters());
    }

    apply_filters() {
        this.filters.status = $('#rental_job_status_filter').val();
        this.load_rental_jobs();
    }

    clear_filters() {
        $('#rental_job_status_filter').val("");
        this.filters.status = null;
        this.load_rental_jobs();
    }

    setup_rental_list_area() {
        this.wrapper.find(".page-content").append('<div class="my-rental-list"></div>');
    }

    load_rental_jobs() {
        let api_filters = {
            // Customer filter will be applied server-side based on logged-in user's User Permissions
            "docstatus": 1 // Show only submitted jobs
        };
        if (this.filters.status) {
            api_filters["status"] = this.filters.status;
        }

        frappe.show_progress(__("Loading Rentals..."), true, false);

        frappe.call({
            method: "frappe.client.get_list", // Standard API, relies on User Permissions for customer filtering
            args: {
                doctype: "Rental Job",
                filters: api_filters,
                fields: [
                    "name", "customer_name", "project_name", "status", 
                    "scheduled_dispatch_date", "scheduled_return_date", 
                    "grand_total", "currency",
                    "custom_customer_facing_status_reason" // Assuming this field exists on Rental Job
                ],
                order_by: "modified desc",
                limit_page_length: 50 
            },
            callback: (r) => {
                frappe.hide_progress();
                if (r.message) {
                    this.rental_jobs = r.message;
                    this.render_rental_jobs();
                } else {
                    this.wrapper.find(".my-rental-list").html(`<p>${__("No rental jobs found matching your criteria.")}</p>`);
                }
            },
            error: (r) => {
                frappe.hide_progress();
                frappe.msgprint({title: __("Error"), message: __("Could not load your rental jobs."), indicator: "red"});
            }
        });
    }

    render_rental_jobs() {
        const container = this.wrapper.find(".my-rental-list");
        container.empty();

        if (!this.rental_jobs || this.rental_jobs.length === 0) {
            container.html(`<p>${__("You have no rental jobs to display.")}</p>`);
            return;
        }

        let list_html = `<div class="list-group">`;
        this.rental_jobs.forEach(job => {
            let status_reason_html = "";
            if (job.custom_customer_facing_status_reason) {
                status_reason_html = `<p class="small text-muted rental-status-reason"><strong>Reason:</strong> ${job.custom_customer_facing_status_reason}</p>`;
            }

            list_html += `
                <a href="/app/rental-job/${job.name}" class="list-group-item my-rental-item">
                    <div class="row">
                        <div class="col-sm-8">
                            <h5 class="list-group-item-heading">${job.project_name || job.name}</h5>
                            <p class="list-group-item-text small text-muted">
                                Customer: ${job.customer_name || 'N/A'} | Job ID: ${job.name}
                            </p>
                        </div>
                        <div class="col-sm-4 text-right">
                            <span class="label label-default rental-status-${job.status.toLowerCase().replace(/ /g, '-')}">${job.status}</span>
                            <p class="small margin-top-xs">
                                ${frappe.datetime.str_to_user(job.scheduled_dispatch_date)} - 
                                ${frappe.datetime.str_to_user(job.scheduled_return_date)}
                            </p>
                            ${job.grand_total ? `<p class="text-muted small">${frappe.format_currency(job.grand_total, job.currency)}</p>` : ''}
                        </div>
                    </div>
                    ${status_reason_html}
                </a>
            `;
        });
        list_html += `</div>`;
        container.html(list_html);
    }
}
