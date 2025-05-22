# Project/onhire_pro/onhire_pro/report/rental_revenue_report/rental_revenue_report.py
import frappe
from frappe import _
from frappe.utils import getdate, flt, add_days, add_months, get_first_day, get_last_day, nowdate
from collections import defaultdict

def execute(filters=None):
    columns, chart_data_config = get_columns(filters) # chart_data_config for dynamic chart labels
    data = get_data(filters, columns, chart_data_config) # Pass chart_data_config
    
    chart = None
    if data and chart_data_config: # Ensure data and config exist for chart
        chart_labels = [d[chart_data_config["label_field"]] for d in data]
        chart_values = [d[chart_data_config["value_field"]] for d in data]
        
        # Ensure unique labels for chart if data is not pre-aggregated by label_field
        if len(chart_labels) != len(set(chart_labels)) and filters.get("group_by"):
            # If grouped, data should already be aggregated. If not, this indicates an issue.
            # For time series (periodicity), labels will be unique periods.
            pass # Assuming data is correctly aggregated if group_by is used.
        
        chart = {
            "type": "line", # Default to line for time series
            "data": {
                'labels': chart_labels,
                'datasets': [{'name': chart_data_config["dataset_label"], 'values': chart_values}]
            },
            "title": _("Rental Revenue Trend")
        }
        if filters.get("group_by"): # If grouped, bar chart might be better
            chart["type"] = "bar"
            chart["title"] = _("Rental Revenue by ") + _(filters.get("group_by"))


    return columns, data, None, chart, None # No separate report summary for now

def get_columns(filters):
    group_by = filters.get("group_by")
    periodicity = filters.get("periodicity", "Monthly") # Default if not set

    columns = []
    chart_config = {"label_field": "period", "value_field": "revenue", "dataset_label": _("Revenue")}


    if group_by:
        if group_by == "Item Group":
            columns.append({"label": _("Item Group"), "fieldname": "group_by_field", "fieldtype": "Link", "options": "Item Group", "width": 180})
            chart_config["label_field"] = "group_by_field"
        elif group_by == "Customer":
            columns.append({"label": _("Customer"), "fieldname": "group_by_field", "fieldtype": "Link", "options": "Customer", "width": 180})
            chart_config["label_field"] = "group_by_field"
        elif group_by == "Sales Person":
            columns.append({"label": _("Sales Person"), "fieldname": "group_by_field", "fieldtype": "Link", "options": "Sales Person", "width": 180})
            chart_config["label_field"] = "group_by_field"
        elif group_by == "Item Code":
            columns.append({"label": _("Item Code"), "fieldname": "group_by_field", "fieldtype": "Link", "options": "Item", "width": 180})
            columns.append({"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200}) # Add item name
            chart_config["label_field"] = "group_by_field"
        else: # Default to period if group_by is invalid or not set for grouping columns
            columns.append({"label": _("Period"), "fieldname": "period", "fieldtype": "Data", "width": 150})
    else: # If not grouping by a field, period is the primary label
        columns.append({"label": _("Period"), "fieldname": "period", "fieldtype": "Data", "width": 150})

    columns.append({"label": _("Revenue"), "fieldname": "revenue", "fieldtype": "Currency", "width": 150})
    # Placeholder for comparison columns, logic for these is complex
    # columns.append({"label": _("Previous Period Revenue"), "fieldname": "prev_period_revenue", "fieldtype": "Currency", "width": 180})
    # columns.append({"label": _("Growth (%)"), "fieldname": "growth_percentage", "fieldtype": "Percent", "width": 120})
    
    return columns, chart_config


def get_data(filters, columns, chart_data_config):
    company = filters.get("company")
    from_date_main = getdate(filters.get("from_date"))
    to_date_main = getdate(filters.get("to_date"))
    periodicity = filters.get("periodicity", "Monthly")
    group_by_field_filter = filters.get("group_by") # Renamed to avoid conflict with variable

    periods = get_report_periods(from_date_main, to_date_main, periodicity)
    
    report_data = []

    for p_start, p_end, p_label in periods:
        sql_params = {
            "company": company,
            "from_date": p_start,
            "to_date": p_end
        }
        
        conditions = ["si.docstatus = 1", "si.company = %(company)s", "sii.docstatus = 1"] 
        conditions.append("si.posting_date BETWEEN %(from_date)s AND %(to_date)s")
        conditions.append("(si.custom_linked_rental_job IS NOT NULL OR item.is_rental_item = 1)")


        if filters.get("customer"):
            conditions.append("si.customer = %(customer)s")
            sql_params["customer"] = filters.get("customer")
        if filters.get("item_code"):
            conditions.append("sii.item_code = %(item_code)s")
            sql_params["item_code"] = filters.get("item_code")
        if filters.get("item_group") and group_by_field_filter != "Item Group": 
            conditions.append("item.item_group = %(item_group_filter)s") 
            sql_params["item_group_filter"] = filters.get("item_group")
        if filters.get("sales_person"):
            sp_field_on_si = "sales_person" if frappe.db.has_column("Sales Invoice", "sales_person") else "owner"
            conditions.append(f"si.{sp_field_on_si} = %(sales_person)s")
            sql_params["sales_person"] = filters.get("sales_person")


        select_fields = "SUM(sii.base_net_amount) as revenue"
        group_by_sql_parts = []
        
        # Determine the field to group by for SQL
        sql_group_by_field_name_for_select = None
        if group_by_field_filter == "Item Group":
            select_fields += ", item.item_group as group_by_field"
            group_by_sql_parts.append("item.item_group")
        elif group_by_field_filter == "Customer":
            select_fields += ", si.customer as group_by_field"
            group_by_sql_parts.append("si.customer")
        elif group_by_field_filter == "Sales Person":
            sp_field = "si.sales_person" if frappe.db.has_column("Sales Invoice", "sales_person") else "si.owner"
            select_fields += f", {sp_field} as group_by_field"
            group_by_sql_parts.append(sp_field)
        elif group_by_field_filter == "Item Code":
            select_fields += ", sii.item_code as group_by_field, item.item_name as item_name_for_report"
            group_by_sql_parts.extend(["sii.item_code", "item.item_name"])

        group_by_sql = ""
        if group_by_sql_parts:
            group_by_sql = f"GROUP BY {', '.join(group_by_sql_parts)}"


        query = f"""
            SELECT {select_fields}
            FROM `tabSales Invoice Item` sii
            JOIN `tabSales Invoice` si ON sii.parent = si.name
            JOIN `tabItem` item ON sii.item_code = item.name 
            WHERE {" AND ".join(conditions)}
            {group_by_sql}
            ORDER BY revenue DESC
        """
        
        period_results = frappe.db.sql(query, sql_params, as_dict=True)

        for row in period_results:
            entry = {"period": p_label, "revenue": flt(row.get("revenue"))} # Use .get for safety
            if group_by_field_filter and "group_by_field" in row:
                entry["group_by_field"] = row.group_by_field
                if group_by_field_filter == "Item Code" and "item_name_for_report" in row:
                    entry["item_name"] = row.item_name_for_report
            report_data.append(entry)
            
    # If not grouping by any field, and periodicity is not 'Overall', aggregate revenue per period
    if not group_by_field_filter and periodicity != "Overall" and len(periods) > 1:
        aggregated_data = defaultdict(float)
        for row in report_data: # report_data here contains one entry per period already if no group_by
            aggregated_data[row["period"]] += row["revenue"] 
        
        final_data = []
        # Sort by period before creating final list to maintain order for charts
        sorted_periods = sorted(aggregated_data.keys(), key=lambda p: get_period_sort_key(p, periodicity, from_date_main))

        for period_label in sorted_periods:
            final_data.append({"period": period_label, "revenue": aggregated_data[period_label]})
        report_data = final_data

    return report_data


def get_report_periods(from_date, to_date, periodicity):
    periods = []
    current_period_start = getdate(from_date)
    final_end = getdate(to_date)

    if periodicity == "Overall" or not periodicity:
        return [(current_period_start, final_end, f"{current_period_start.strftime('%Y-%m-%d')} to {final_end.strftime('%Y-%m-%d')}")]

    while current_period_start <= final_end:
        period_label = ""
        next_period_start = None # Define it to ensure it's set in all branches
        if periodicity == "Daily":
            period_end = current_period_start
            period_label = current_period_start.strftime("%Y-%m-%d")
            next_period_start = add_days(current_period_start, 1)
        elif periodicity == "Weekly":
            # Ensure week starts consistently e.g. Monday
            days_to_monday = current_period_start.weekday()
            actual_week_start = add_days(current_period_start, -days_to_monday)
            if actual_week_start < getdate(from_date) and current_period_start == getdate(from_date) : # If first period, align with from_date
                 actual_week_start = current_period_start

            period_end = add_days(actual_week_start, 6)
            if period_end > final_end: period_end = final_end
            if actual_week_start > final_end: break

            period_label = f"{actual_week_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}"
            next_period_start = add_days(period_end, 1)
            current_period_start = actual_week_start # Use actual start for this period
        elif periodicity == "Monthly":
            actual_period_start = get_first_day(current_period_start)
            period_end = get_last_day(actual_period_start)
            if period_end > final_end: period_end = final_end
            if actual_period_start > final_end : break 
            period_label = actual_period_start.strftime("%b %Y")
            next_period_start = add_months(actual_period_start, 1)
            current_period_start = actual_period_start
        elif periodicity == "Quarterly":
            month = current_period_start.month
            year = current_period_start.year
            if month <= 3: quarter_start_month = 1
            elif month <= 6: quarter_start_month = 4
            elif month <= 9: quarter_start_month = 7
            else: quarter_start_month = 10
            
            actual_period_start = getdate(f"{year}-{quarter_start_month:02d}-01")
            period_end = get_last_day(add_months(actual_period_start, 2))
            if period_end > final_end: period_end = final_end
            if actual_period_start > final_end : break
            period_label = f"Q{(quarter_start_month-1)//3 + 1} {year}"
            next_period_start = add_months(actual_period_start, 3)
            current_period_start = actual_period_start
        elif periodicity == "Yearly":
            actual_period_start = get_first_day(current_period_start).replace(month=1, day=1)
            period_end = get_last_day(actual_period_start).replace(month=12, day=31)
            if period_end > final_end: period_end = final_end
            if actual_period_start > final_end : break
            period_label = actual_period_start.strftime("%Y")
            next_period_start = add_months(actual_period_start, 12)
            current_period_start = actual_period_start
        else: 
            break 
        
        periods.append((current_period_start, period_end, period_label))
        
        if not next_period_start or next_period_start > final_end: # Break if next period starts after final_end
            break
        current_period_start = next_period_start
            
    return periods

def get_period_sort_key(period_label, periodicity, overall_from_date):
    # Helper to sort periods correctly for charts if they are not naturally sorted by string
    try:
        if periodicity == "Monthly":
            return getdate(f"01-{period_label}") # "Jan 2023" -> "01-Jan-2023"
        elif periodicity == "Quarterly": # Q1 2023
            q, year = period_label.split(" ")
            month = (int(q[1])-1)*3 + 1
            return getdate(f"{year}-{month:02d}-01")
        elif periodicity == "Yearly":
            return getdate(f"{period_label}-01-01")
        elif periodicity == "Weekly" or periodicity == "Daily":
             return getdate(period_label.split(" to ")[0]) # Use start of week/day
    except:
        return getdate(overall_from_date) # Fallback
    return getdate(overall_from_date)
