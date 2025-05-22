frappe.pages['my-documents'].on_page_load = function(wrapper) {
    frappe.my_documents_view = new MyDocumentsView(wrapper);
}

class MyDocumentsView {
    constructor(wrapper) {
        this.wrapper = $(wrapper);
        this.page = wrapper.page;
        this.documents = [];
        this.make();
    }

    make() {
        this.setup_page_head();
        this.setup_document_list_area();
        this.load_documents();
    }

    setup_page_head() {
        this.page.set_title(__("My Documents"));
        this.page.add_button(__("Export Rental History (CSV)"), () => {
            this.export_rental_history();
        }, {icon: "fa fa-download"});
    }

    setup_document_list_area() {
        this.wrapper.find(".page-content").append('<div class="my-document-list"></div>');
    }

    load_documents() {
        frappe.show_progress(__("Loading Documents..."), true, false);
        // Server-side filtering by customer is assumed via User Permissions
        frappe.call({
            method: "onhire_pro.onhire_pro.customer_portal.utils.get_customer_documents", // New util function
            callback: (r) => {
                frappe.hide_progress();
                if (r.message && r.message.documents) {
                    this.documents = r.message.documents;
                    this.render_documents();
                } else {
                    this.wrapper.find(".my-document-list").html(`<p>${__("No documents found.")}</p>`);
                     if(r.message && r.message.error) {
                        frappe.msgprint({title: __("Error"), message: r.message.error, indicator: "red"});
                    }
                }
            },
            error: (r) => {
                frappe.hide_progress();
                frappe.msgprint({title: __("Error"), message: __("Could not load your documents."), indicator: "red"});
            }
        });
    }

    render_documents() {
        const container = this.wrapper.find(".my-document-list");
        container.empty();

        if (!this.documents || this.documents.length === 0) {
            container.html(`<p>${__("You have no documents to display.")}</p>`);
            return;
        }

        let table_html = `
            <table class="table table-striped table-bordered">
                <thead>
                    <tr>
                        <th>${__("Document ID")}</th>
                        <th>${__("Type")}</th>
                        <th>${__("Date")}</th>
                        <th>${__("Status")}</th>
                        <th>${__("Amount")}</th>
                        <th>${__("Actions")}</th>
                    </tr>
                </thead>
                <tbody>
        `;

        this.documents.forEach(doc => {
            let amount_html = doc.grand_total ? frappe.format_currency(doc.grand_total, doc.currency || frappe.boot.sysdefaults.currency) : '';
            // CP_RENTAL.8.2: Implement PDF Download for Individual Documents
            let pdf_link = `/api/method/frappe.utils.print_format.download_pdf?doctype=${encodeURIComponent(doc.doctype)}&name=${encodeURIComponent(doc.name)}&format=Standard&no_letterhead=0`;
            
            table_html += `
                <tr>
                    <td><a href="/app/${doc.doctype.toLowerCase().replace(/ /g, "-")}/${doc.name}">${doc.name}</a></td>
                    <td>${doc.doctype}</td>
                    <td>${frappe.datetime.str_to_user(doc.transaction_date || doc.posting_date || doc.creation)}</td>
                    <td><span class="label label-default status-${doc.status.toLowerCase().replace(/ /g, '-')}">${doc.status || 'N/A'}</span></td>
                    <td>${amount_html}</td>
                    <td><a href="${pdf_link}" class="btn btn-xs btn-info" target="_blank"><i class="fa fa-file-pdf-o"></i> ${__("PDF")}</a></td>
                </tr>
            `;
        });

        table_html += `
                </tbody>
            </table>
        `;
        container.html(table_html);
    }

    export_rental_history() {
        // CP_RENTAL.8.3: Implement Export for Rental History (CSV/Excel)
        frappe.show_progress(__("Generating Report..."), true, false);
        frappe.call({
            method: "onhire_pro.onhire_pro.customer_portal.utils.export_customer_rental_history", // New util function
            callback: (r) => {
                frappe.hide_progress();
                if (r.message && r.message.csv_data) {
                    // Trigger download
                    let filename = `rental_history_${frappe.session.user}_${frappe.datetime.now_date()}.csv`;
                    frappe.tools.downloadify(r.message.csv_data, null, filename);
                } else if (r.message && r.message.error) {
                     frappe.msgprint({title: __("Error"), message: r.message.error, indicator: "red"});
                } else {
                    frappe.msgprint({title: __("Export Failed"), message: __("Could not generate rental history report."), indicator: "red"});
                }
            },
            error: (r) => {
                frappe.hide_progress();
                frappe.msgprint({title: __("Error"), message: __("Failed to export rental history."), indicator: "red"});
            }
        });
    }
}
