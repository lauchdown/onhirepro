frappe.web_form.on('custom_rental_start_date', (field, value) => {
    trigger_quote_preview_update(field.web_form);
});
frappe.web_form.on('custom_rental_end_date', (field, value) => {
    trigger_quote_preview_update(field.web_form);
});

frappe.web_form.on('items', {
    item_code: (frm, cdt, cdn) => { // When item_code changes in a row
        trigger_quote_preview_update(frm.web_form);
    },
    qty: (frm, cdt, cdn) => { // When qty changes in a row
        trigger_quote_preview_update(frm.web_form);
    },
    items_remove: (frm, cdt, cdn) => { // When a row is removed
        trigger_quote_preview_update(frm.web_form);
    },
    items_add: (frm, cdt, cdn) => { // When a new row is added (might initially be empty)
        // Delay slightly to allow item_code to be set if user is quick
        setTimeout(() => trigger_quote_preview_update(frm.web_form), 500);
    }
});


function trigger_quote_preview_update(web_form_doc) {
    // Debounce function to prevent too many API calls
    if (web_form_doc.debounced_update_preview) {
        clearTimeout(web_form_doc.debounced_update_preview);
    }
    web_form_doc.debounced_update_preview = setTimeout(() => {
        update_quote_preview(web_form_doc);
    }, 800); // Adjust delay as needed (e.g., 800ms)
}


function update_quote_preview(web_form_doc) {
    const values = web_form_doc.get_values();
    const start_date = values.custom_rental_start_date;
    const end_date = values.custom_rental_end_date;
    const items_table = values.items || [];

    if (!start_date || !end_date || items_table.length === 0) {
        web_form_doc.fields_dict.custom_quote_preview_html.html("<p class='text-muted'>Please select items and rental dates for an estimate.</p>");
        return;
    }
    
    if (frappe.datetime.str_to_obj(start_date) > frappe.datetime.str_to_obj(end_date)) {
        web_form_doc.fields_dict.custom_quote_preview_html.html("<p class='text-danger'>Start date cannot be after end date.</p>");
        return;
    }

    let items_data = items_table.filter(item => item.item_code && item.qty > 0).map(item => {
        return { item_code: item.item_code, qty: item.qty };
    });

    if (items_data.length === 0) {
        web_form_doc.fields_dict.custom_quote_preview_html.html("<p class='text-muted'>Please add items with quantities.</p>");
        return;
    }
    
    // Display loading state
    web_form_doc.fields_dict.custom_quote_preview_html.html("<p class='text-muted'><i>Calculating estimate...</i></p>");

    frappe.call({
        method: "onhire_pro.onhire_pro.customer_portal.utils.get_rental_quote_estimate",
        args: {
            items_data: JSON.stringify(items_data),
            start_date_str: start_date,
            end_date_str: end_date,
            customer: values.customer // Assuming customer is auto-filled and available
        },
        callback: function(r) {
            if (r.message && !r.message.error) {
                let estimate = r.message;
                let html = `
                    <table class="table table-bordered table-sm" style="width: auto;">
                        <tbody>
                            <tr><td>Rental Days:</td><td>${estimate.rental_days}</td></tr>
                            <tr><td>Subtotal:</td><td>${frappe.format_currency(estimate.sub_total, estimate.currency)}</td></tr>`;
                if (estimate.total_surcharges > 0) {
                    html += `<tr><td>Surcharges:</td><td>${frappe.format_currency(estimate.total_surcharges, estimate.currency)}</td></tr>`;
                }
                if (estimate.total_discounts > 0) {
                    html += `<tr><td>Discounts:</td><td>-${frappe.format_currency(estimate.total_discounts, estimate.currency)}</td></tr>`;
                }
                if (estimate.tax_amount > 0) { // Assuming tax_amount is part of the response
                    html += `<tr><td>Estimated Tax:</td><td>${frappe.format_currency(estimate.tax_amount, estimate.currency)}</td></tr>`;
                }
                html += `   <tr><td><strong>Estimated Total:</strong></td><td><strong>${frappe.format_currency(estimate.grand_total, estimate.currency)}</strong></td></tr>
                        </tbody>
                    </table>
                    <p class="small text-muted">This is an estimate. Final charges may vary. Breakdown:</p>
                    <ul class="list-unstyled small">`;

                estimate.line_items_breakdown.forEach(line => {
                    html += `<li>${line.qty} x ${line.item_name || line.item_code} @ ${frappe.format_currency(line.rate_per_day, estimate.currency)}/day for ${line.rental_days} days = ${frappe.format_currency(line.line_total, estimate.currency)}</li>`;
                     if(line.error){ html += `<li class='text-danger'> - Error: ${line.error}</li>`;}
                });
                html += `</ul>`;
                web_form_doc.fields_dict.custom_quote_preview_html.html(html);
            } else if (r.message && r.message.error) {
                web_form_doc.fields_dict.custom_quote_preview_html.html(`<p class="text-danger">Error: ${r.message.error}</p>`);
            } else {
                web_form_doc.fields_dict.custom_quote_preview_html.html("<p class='text-danger'>Could not calculate estimate at this time.</p>");
            }
        },
        error: function(r) {
            web_form_doc.fields_dict.custom_quote_preview_html.html("<p class='text-danger'>Error calling estimation service.</p>");
        }
    });
}

// Auto-fill customer and company if logged in
frappe.ready(function() {
    if (frappe.session.user !== "Guest") {
        // Get customer linked to the user
        frappe.call({
            method: "onhire_pro.onhire_pro.customer_portal.utils.get_current_user_customer_details", // This new util function is needed
            callback: function(r) {
                if (r.message && r.message.customer_name) {
                    frappe.web_form.set_value("customer", r.message.customer_name);
                    if (r.message.company) {
                         frappe.web_form.set_value("company", r.message.company);
                    }
                    // Trigger initial quote preview if dates and items are somehow prefilled (unlikely for new form)
                    // trigger_quote_preview_update(frappe.web_form); 
                }
            }
        });
    }
});
