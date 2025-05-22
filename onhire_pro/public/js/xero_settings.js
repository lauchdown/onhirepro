frappe.ui.form.on('Xero Settings', {
    refresh: function(frm) {
        frm.add_custom_button(__('Authorize Xero'), function() {
            frappe.call({
                method: 'get_authorization_url',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        window.open(r.message, '_blank');
                    }
                }
            });
        });
        
        if (frm.doc.authorization_status === 'Authorized') {
            frm.add_custom_button(__('Test Connection'), function() {
                frappe.call({
                    method: 'onhire_pro.xero_integration.test_connection',
                    callback: function(r) {
                        if (r.message) {
                            frappe.show_alert({
                                message: __('Connection successful'),
                                indicator: 'green'
                            });
                        }
                    }
                });
            });
        }
    },
    
    enabled: function(frm) {
        if (!frm.doc.enabled) {
            frappe.confirm(
                __('Disabling Xero integration will clear all stored credentials. Continue?'),
                function() {
                    frm.set_value('access_token', '');
                    frm.set_value('refresh_token', '');
                    frm.set_value('token_expiry', '');
                    frm.set_value('tenant_id', '');
                    frm.set_value('authorization_status', 'Not Authorized');
                    frm.save();
                }
            );
        }
    }
});
