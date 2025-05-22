frappe.pages['rental-catalog'].on_page_load = function(wrapper) {
    frappe.rental_catalog = new RentalCatalog(wrapper);
}

class RentalCatalog {
    constructor(wrapper) {
        this.wrapper = $(wrapper);
        this.page = wrapper.page;
        this.settings = {
            items_per_page: 12,
            // Add other settings if needed
        };
        this.filters = {
            start_date: null,
            end_date: null,
            item_group: null,
            search_term: ''
        };
        this.items = [];
        this.make();
    }

    make() {
        this.setup_page_head();
        this.setup_filters_area();
        this.setup_item_display_area();
        this.load_items();
    }

    setup_page_head() {
        this.page.set_title("Rental Catalog");
        // Add any primary actions if needed, e.g., "New Booking Request"
        // this.page.set_primary_action("New Request", () => {
        //     frappe.set_route("booking-request"); // Assuming a route for booking form
        // });
    }

    setup_filters_area() {
        let filters_html = `
            <div class="row rental-catalog-filters" style="margin-bottom: 20px; padding: 15px; background-color: #f9f9f9; border-radius: 4px;">
                <div class="col-md-3">
                    <label for="rental_start_date">Rental Start Date</label>
                    <input type="text" id="rental_start_date" class="form-control">
                </div>
                <div class="col-md-3">
                    <label for="rental_end_date">Rental End Date</label>
                    <input type="text" id="rental_end_date" class="form-control">
                </div>
                <div class="col-md-3">
                    <label for="rental_item_group">Item Group</label>
                    <select id="rental_item_group" class="form-control">
                        <option value="">All Groups</option>
                        <!-- Item groups will be populated here -->
                    </select>
                </div>
                <div class="col-md-3">
                    <label for="rental_search_term">Search</label>
                    <input type="text" id="rental_search_term" class="form-control" placeholder="Search by name, code...">
                </div>
            </div>
            <div class="row">
                <div class="col-md-12">
                    <button class="btn btn-primary btn-sm" id="apply_catalog_filters">Apply Filters</button>
                    <button class="btn btn-default btn-sm" id="clear_catalog_filters" style="margin-left: 5px;">Clear Filters</button>
                </div>
            </div>
        `;
        this.wrapper.find(".page-content").append(filters_html);

        // Initialize date pickers
        this.start_date_picker = frappe.ui.form.make_control({
            parent: this.wrapper.find('#rental_start_date').parent(),
            df: { fieldname: 'rental_start_date', fieldtype: 'Date', label: 'Rental Start Date' },
            render_input: true,
        });
        this.end_date_picker = frappe.ui.form.make_control({
            parent: this.wrapper.find('#rental_end_date').parent(),
            df: { fieldname: 'rental_end_date', fieldtype: 'Date', label: 'Rental End Date' },
            render_input: true,
        });
        
        // Remove labels created by make_control as we have them already
        this.wrapper.find('#rental_start_date').parent().find('.control-label').remove();
        this.wrapper.find('#rental_end_date').parent().find('.control-label').remove();


        // Populate item groups
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item Group",
                filters: { "is_group": 0 }, // Show only leaf nodes
                fields: ["name"],
                order_by: "name asc"
            },
            callback: (r) => {
                if (r.message) {
                    r.message.forEach(group => {
                        $('#rental_item_group').append(`<option value="${group.name}">${group.name}</option>`);
                    });
                }
            }
        });

        // Filter button actions
        $('#apply_catalog_filters').on('click', () => this.apply_filters());
        $('#clear_catalog_filters').on('click', () => this.clear_filters());
        $('#rental_search_term').on('keypress', (e) => {
            if (e.which == 13) { // Enter key
                this.apply_filters();
            }
        });
    }
    
    apply_filters() {
        this.filters.start_date = this.start_date_picker.get_value();
        this.filters.end_date = this.end_date_picker.get_value();
        this.filters.item_group = $('#rental_item_group').val();
        this.filters.search_term = $('#rental_search_term').val();

        if (this.filters.start_date && this.filters.end_date && frappe.datetime.str_to_obj(this.filters.start_date) > frappe.datetime.str_to_obj(this.filters.end_date)) {
            frappe.msgprint({title: "Filter Error", message: "Start date cannot be after end date.", indicator: "red"});
            return;
        }
        this.load_items();
    }

    clear_filters() {
        this.start_date_picker.set_value(null);
        this.end_date_picker.set_value(null);
        $('#rental_item_group').val("");
        $('#rental_search_term').val("");
        this.filters = { start_date: null, end_date: null, item_group: null, search_term: '' };
        this.load_items();
    }

    setup_item_display_area() {
        this.wrapper.find(".page-content").append('<div class="rental-item-list row"></div>');
        this.wrapper.find(".page-content").append('<div id="pagination-area" class="text-center"></div>');
    }

    load_items() {
        let api_filters = {
            "is_rental_item": 1,
            "disabled": 0
        };
        if (this.filters.item_group) {
            api_filters["item_group"] = this.filters.item_group;
        }
        if (this.filters.search_term) {
            // Search in item_code, item_name, description
            // This requires OR filtering on server-side if using frappe.client.get_list directly with complex filters
            // For simplicity, we'll pass search_term and let server handle it if possible, or filter client-side for basic demo
            // A dedicated API endpoint for catalog search would be better.
             api_filters["name"] = ["like", `%${this.filters.search_term}%`]; // Basic search on name/code
        }

        frappe.show_progress(__("Loading Items..."),true ,false);

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item",
                filters: api_filters,
                fields: ["name", "item_code", "item_name", "item_group", "description", "image", "standard_rate", "custom_rental_specifications"], // Assuming custom_rental_specifications field
                order_by: "item_name asc",
                limit_page_length: 1000 // Fetch more and handle client-side or implement server-side pagination
            },
            callback: (r) => {
                frappe.hide_progress();
                if (r.message) {
                    this.items = r.message;
                    if (this.filters.start_date && this.filters.end_date) {
                        this.check_availability_and_render();
                    } else {
                        this.render_items(this.items);
                    }
                } else {
                    this.wrapper.find(".rental-item-list").html("<p>No rental items found matching your criteria.</p>");
                }
            },
            error: (r) => {
                frappe.hide_progress();
                frappe.msgprint({title: "Error", message: "Could not load rental items.", indicator: "red"});
            }
        });
    }

    check_availability_and_render() {
        // CP_RENTAL.4.2: Implement Dynamic Availability Filtering
        // This requires a backend method to check availability for multiple items.
        // For now, this is a placeholder. The actual check would involve:
        // 1. Collecting all item_codes from this.items
        // 2. Calling a whitelisted backend method: e.g., get_items_availability(item_codes, start_date, end_date)
        // 3. Backend method checks stock ledger or Rental Event conflicts for each item.
        // 4. Backend returns a map: { item_code: { available: true/false, reason: "..." } }
        // 5. Client-side then filters or annotates items before rendering.

        frappe.show_progress(__("Checking Availability..."), true, false);
        const item_codes = this.items.map(item => item.item_code);

        frappe.call({
            method: "onhire_pro.onhire_pro.customer_portal.utils.check_multiple_item_availability", // Assuming this method exists
            args: {
                item_codes: JSON.stringify(item_codes),
                start_date: this.filters.start_date,
                end_date: this.filters.end_date
            },
            callback: (r) => {
                frappe.hide_progress();
                if (r.message && r.message.availability_map) {
                    const availability_map = r.message.availability_map;
                    let available_items = this.items.filter(item => {
                        const item_avail = availability_map[item.item_code];
                        return item_avail && item_avail.available;
                    });
                    this.render_items(available_items, availability_map);
                } else {
                    frappe.msgprint({title: "Availability Check", message: "Could not check item availability. Displaying all items.", indicator: "orange"});
                    this.render_items(this.items); // Fallback to rendering all if availability check fails
                }
            },
            error: (r) => {
                frappe.hide_progress();
                frappe.msgprint({title: "Error", message: "Error checking item availability. Displaying all items.", indicator: "red"});
                this.render_items(this.items);
            }
        });
    }


    render_items(items_to_render, availability_map = {}) {
        const item_list_container = this.wrapper.find(".rental-item-list");
        item_list_container.empty();

        if (!items_to_render || items_to_render.length === 0) {
            item_list_container.html("<p>No rental items found matching your criteria.</p>");
            return;
        }

        items_to_render.forEach(item => {
            let image_html = item.image ? `<img src="${item.image}" class="img-responsive rental-item-image" alt="${item.item_name}">` : `<div class="rental-item-no-image">No Image</div>`;
            let availability_html = '';
            if (this.filters.start_date && this.filters.end_date) {
                const item_avail_info = availability_map[item.item_code];
                if (item_avail_info) {
                    availability_html = item_avail_info.available 
                        ? `<span class="text-success">Available</span>` 
                        : `<span class="text-danger">Unavailable</span> ${item_avail_info.reason ? '('+item_avail_info.reason+')' : ''}`;
                } else {
                    availability_html = `<span class="text-muted">Availability not checked</span>`; // Should not happen if check_availability_and_render was called
                }
            }

            let item_card_html = `
                <div class="col-md-4 col-sm-6 rental-item-card-wrapper">
                    <div class="rental-item-card">
                        <div class="rental-item-image-container">
                            ${image_html}
                        </div>
                        <h5>${item.item_name} (${item.item_code})</h5>
                        <p class="text-muted small">${item.item_group}</p>
                        <p class="item-description">${frappe.ellipsis(item.description || "No description available.", 100)}</p>
                        ${item.custom_rental_specifications ? `<p class="small"><strong>Specs:</strong> ${item.custom_rental_specifications}</p>` : ''}
                        <p><strong>Price:</strong> ${item.standard_rate ? frappe.format_currency(item.standard_rate) : 'Contact for Price'}</p>
                        ${availability_html ? `<p><strong>Availability:</strong> ${availability_html}</p>` : ''}
                        <a href="/app/item/${item.item_code}" class="btn btn-xs btn-default">View Details</a>
                        <!-- Add to cart/request button can go here -->
                    </div>
                </div>
            `;
            item_list_container.append(item_card_html);
        });
        // Basic pagination can be added here if needed
    }
}
