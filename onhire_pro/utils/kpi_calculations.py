import frappe
from frappe.utils import nowdate, add_days, date_diff, getdate, add_months
from onhire_pro.reports.kpi_utils import (
    calculate_item_utilization_rate,
    calculate_average_rental_duration,
    get_revenue_per_item_category,
    calculate_avg_maintenance_turnaround_time,
    calculate_booking_conversion_rate,
    calculate_customer_churn_rate,
    calculate_damage_rate,
    get_total_cost_of_damages,
    get_stock_reservation_conflicts,
    get_overdue_returns_count,
    get_active_rental_jobs_count,
    get_jobs_due_for_dispatch_count,
    get_jobs_due_for_return_count,
    get_at_risk_stock_count,
    get_items_awaiting_assessment_count,
    get_items_in_maintenance_count,
    get_total_rental_revenue,
    get_open_rental_quotation_value,
    get_overdue_invoice_amount,
    get_average_revenue_per_rental_job,
    get_rental_revenue_trend,
    get_job_status_distribution,
    get_top_5_most_rented_items,
    get_top_5_customers_by_rental_value,
    get_damage_rate_by_item_group,
    get_item_utilization_rate_trend,
    calculate_active_rental_jobs
)

# This file is deprecated and will be removed in a future version.
# All KPI calculation functions have been moved to onhire_pro.reports.kpi_utils
# Please update your imports to use the new module.

frappe.log_error(
    "The module onhire_pro.utils.kpi_calculations is deprecated. "
    "Please use onhire_pro.reports.kpi_utils instead.",
    "Deprecation Warning"
)

# Forward all functions to maintain backward compatibility
