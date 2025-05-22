frappe.pages['xero-sync-dashboard'].on_page_load = function(wrapper) {
  frappe.ui.make_app_page({
    parent: wrapper,
    title: 'Xero Sync Dashboard',
    single_column: true
  });

  new XeroSyncDashboard(wrapper);
};

class XeroSyncDashboard {
  constructor(wrapper) {
    this.page = wrapper.page;
    this.wrapper = $(wrapper);
    this.filters = {};
    this.setup_page();
  }

  setup_page() {
    this.setup_filters();
    this.setup_refresh();
    this.setup_stats_section();
    this.setup_failed_syncs_section();
    this.refresh();
  }

  setup_filters() {
    this.page.add_field({
      fieldname: 'date_range',
      label: 'Date Range',
      fieldtype: 'DateRange',
      default: [
        frappe.datetime.add_days(frappe.datetime.now_date(), -30),
        frappe.datetime.now_date()
      ],
      change: () => this.refresh()
    });

    this.page.add_field({
      fieldname: 'sync_status',
      label: 'Sync Status',
      fieldtype: 'Select',
      options: '\nNot Synced\nIn Progress\nSynced\nFailed',
      change: () => this.refresh()
    });
  }

  setup_refresh() {
    this.page.set_primary_action('Refresh', () => this.refresh());
    this.page.set_secondary_action('Retry Failed', () => this.retry_all_failed());
  }

  setup_stats_section() {
    this.stats_section = $('<div class="sync-stats-section">').appendTo(this.wrapper);
  }

  setup_failed_syncs_section() {
    this.failed_syncs_section = $('<div class="failed-syncs-section">').appendTo(this.wrapper);
  }

  refresh() {
    this.get_filters();
    this.fetch_data();
  }

  get_filters() {
    this.filters = {
      date_range: this.page.fields_dict.date_range.get_value(),
      sync_status: this.page.fields_dict.sync_status.get_value()
    };
  }

  fetch_data() {
    frappe.call({
      method: 'onhire_pro.onhire_pro.page.xero_sync_dashboard.xero_sync_dashboard.get_dashboard_data',
      args: {
        filters: this.filters
      },
      callback: (r) => {
        if (r.message) {
          this.render_stats(r.message.stats);
          this.render_failed_syncs(r.message.failed_syncs);
        }
      }
    });
  }

  render_stats(stats) {
    const html = `
      <div class="stats-container">
        <div class="stat-box">
          <div class="stat-value">${stats.total_syncs}</div>
          <div class="stat-label">Total Syncs</div>
        </div>
        <div class="stat-box">
          <div class="stat-value success">${stats.successful_syncs}</div>
          <div class="stat-label">Successful</div>
        </div>
        <div class="stat-box">
          <div class="stat-value pending">${stats.pending_syncs}</div>
          <div class="stat-label">Pending</div>
        </div>
        <div class="stat-box">
          <div class="stat-value error">${stats.failed_syncs}</div>
          <div class="stat-label">Failed</div>
        </div>
      </div>
    `;

    this.stats_section.html(html);
  }

  render_failed_syncs(failed_syncs) {
    if (!failed_syncs.length) {
      this.failed_syncs_section.html('<div class="no-failed-syncs">No failed syncs found</div>');
      return;
    }

    const html = `
      <div class="failed-syncs-container">
        <h3>Failed Syncs</h3>
        <div class="failed-syncs-table">
          <table class="table table-bordered">
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Customer</th>
                <th>Amount</th>
                <th>Last Attempt</th>
                <th>Error</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${failed_syncs.map(sync => `
                <tr>
                  <td>
                    <a href="/app/sales-invoice/${sync.name}">${sync.name}</a>
                  </td>
                  <td>${sync.customer_name}</td>
                  <td>${format_currency(sync.grand_total, sync.currency)}</td>
                  <td>${frappe.datetime.str_to_user(sync.xero_last_sync_attempt)}</td>
                  <td class="error-message">${sync.error_message || 'Unknown error'}</td>
                  <td>
                    <button class="btn btn-xs btn-primary retry-sync" 
                            data-invoice="${sync.name}">
                      Retry
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    this.failed_syncs_section.html(html);
    this.setup_retry_handlers();
  }

  setup_retry_handlers() {
    this.failed_syncs_section.find('.retry-sync').on('click', (e) => {
      const invoice = $(e.currentTarget).data('invoice');
      this.retry_sync(invoice);
    });
  }

  retry_sync(invoice_name) {
    frappe.confirm(
      `Are you sure you want to retry syncing invoice ${invoice_name}?`,
      () => {
        frappe.call({
          method: 'onhire_pro.xero_integration.sync_invoice_to_xero',
          args: { invoice_name },
          freeze: true,
          freeze_message: __('Retrying sync...'),
          callback: (r) => {
            if (r.message) {
              frappe.show_alert({
                message: __('Sync retry initiated successfully'),
                indicator: 'green'
              });
              this.refresh();
            }
          }
        });
      }
    );
  }

  retry_all_failed() {
    frappe.confirm(
      'Are you sure you want to retry all failed syncs?',
      () => {
        frappe.call({
          method: 'onhire_pro.xero_integration.retry_failed_syncs',
          freeze: true,
          freeze_message: __('Retrying all failed syncs...'),
          callback: (r) => {
            frappe.show_alert({
              message: __('Retry of all failed syncs initiated'),
              indicator: 'green'
            });
            this.refresh();
          }
        });
      }
    );
  }
}
