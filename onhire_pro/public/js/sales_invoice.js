frappe.ui.form.on('Sales Invoice', {
  refresh: function(frm) {
    // Only show for submitted invoices that haven't been synced
    if (frm.doc.docstatus === 1 && (!frm.doc.xero_invoice_id || frm.doc.xero_sync_status === 'Failed')) {
      frm.add_custom_button(__('Send to Xero'), function() {
        frappe.confirm(
          'Are you sure you want to sync this invoice to Xero?',
          function() {
            frappe.call({
              method: 'onhire_pro.xero_integration.sync_invoice_to_xero',
              args: {
                invoice_name: frm.doc.name
              },
              freeze: true,
              freeze_message: __('Sending to Xero...'),
              callback: function(r) {
                if (r.message) {
                  frappe.show_alert({
                    message: __('Invoice sent to Xero successfully'),
                    indicator: 'green'
                  });
                  frm.reload_doc();
                }
              },
              error: function(r) {
                frappe.msgprint({
                  title: __('Sync Failed'),
                  indicator: 'red',
                  message: __(r._server_messages || 'Failed to sync with Xero. Please try again later.')
                });
              }
            });
          }
        );
      }, __('Integrations'));
    }
    
    // Show Xero status indicators
    if (frm.doc.xero_sync_status) {
      let indicator = {
        'Not Synced': 'gray',
        'In Progress': 'orange',
        'Synced': 'green',
        'Failed': 'red'
      }[frm.doc.xero_sync_status];
      
      frm.dashboard.add_indicator(
        __(`Xero: ${frm.doc.xero_sync_status}`),
        indicator
      );
    }
  }
});
