app_include_js = [
    "/assets/onhire_pro/js/xero_settings.js",
    "/assets/onhire_pro/js/sales_invoice.js"
]

doc_events = {
    "Sales Invoice": {
        "on_submit": "onhire_pro.xero_integration.sync_invoice_to_xero"
    }
}

scheduler_events = {
    "hourly": [
        "onhire_pro.xero_integration.setup_xero_sync_scheduler"
    ]
}
