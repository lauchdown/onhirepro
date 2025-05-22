# Project/onhire_pro/onhire_pro/report/rental_item_availability_calendar/rental_item_availability_calendar.py
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, add_days, get_datetime_str

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    # Chart and summary are not typically used when rendering a custom calendar like this in a script report
    return columns, data, None, None, None 

def get_columns(filters):
    # These columns are for the underlying data table, which might be hidden or less prominent
    # if the main focus is the calendar visualization injected by JS.
    return [
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 120
        },
        {
            "label": _("Serial No"),
            "fieldname": "serial_no",
            "fieldtype": "Link",
            "options": "Serial No",
            "width": 120
        },
        {
            "label": _("Event Type"), # 'Rental Job' or 'Maintenance Task'
            "fieldname": "event_type",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Reference Doctype"),
            "fieldname": "reference_doctype",
            "fieldtype": "Data",
            "hidden": 1
        },
        {
            "label": _("Reference Name"),
            "fieldname": "reference_name",
            "fieldtype": "Dynamic Link",
            "options": "reference_doctype",
            "width": 150
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Start Date"),
            "fieldname": "start_date",
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "label": _("End Date"),
            "fieldname": "end_date",
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        }
    ]

def get_data(filters):
    data = []
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    item_code_filter = filters.get("item_code")
    item_group_filter = filters.get("item_group")
    event_type_filter = filters.get("status") # Filter name is 'status' in JS, maps to event_type

    sql_params = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date
    }

    # Fetch Rental Jobs
    if not event_type_filter or event_type_filter == "Rental Job":
        rj_conditions = ""
        current_sql_params_rj = sql_params.copy()
        if item_code_filter:
            rj_conditions += " AND rji.item_code = %(item_code)s"
            current_sql_params_rj["item_code"] = item_code_filter
        if item_group_filter:
            rj_conditions += " AND item.item_group = %(item_group)s"
            current_sql_params_rj["item_group"] = item_group_filter
        
        rental_jobs_query = f"""
            SELECT 
                rji.item_code, 
                rji.serial_no,
                'Rental Job' as event_type,
                rj.name as reference_name,
                'Rental Job' as reference_doctype,
                rj.status,
                rj.scheduled_dispatch_date as start_date,
                rj.scheduled_return_date as end_date,
                rj.customer
            FROM `tabRental Job Item` rji
            JOIN `tabRental Job` rj ON rji.parent = rj.name
            {'JOIN `tabItem` item ON rji.item_code = item.name' if item_group_filter else ''}
            WHERE rj.docstatus = 1
              AND rj.company = %(company)s
              AND rj.status NOT IN ('Cancelled', 'Draft')
              AND rj.scheduled_dispatch_date <= %(to_date)s
              AND rj.scheduled_return_date >= %(from_date)s
              {rj_conditions}
        """
        rental_job_data = frappe.db.sql(rental_jobs_query, current_sql_params_rj, as_dict=True)
        data.extend(rental_job_data)

    # Fetch Maintenance Tasks
    if (not event_type_filter or event_type_filter == "Maintenance Task") and frappe.db.exists("DocType", "Maintenance Task"):
        mt_conditions = ""
        current_sql_params_mt = sql_params.copy()

        # Check for company field in Maintenance Task
        mt_company_filter = ""
        if frappe.db.has_column("Maintenance Task", "company"):
            mt_company_filter = "AND mt.company = %(company)s"
        else:
            if "company" in current_sql_params_mt: # remove if not applicable
                 del current_sql_params_mt["company"]


        if item_code_filter and frappe.db.has_column("Maintenance Task", "item_code"):
            mt_conditions += " AND mt.item_code = %(item_code)s"
            current_sql_params_mt["item_code"] = item_code_filter
        
        item_join_mt = ""
        if item_group_filter and frappe.db.has_column("Maintenance Task", "item_code"):
            item_join_mt = " JOIN `tabItem` item ON mt.item_code = item.name "
            mt_conditions += " AND item.item_group = %(item_group)s"
            current_sql_params_mt["item_group"] = item_group_filter

        # Determine date fields for Maintenance Task
        start_date_field_mt = "mt.start_date" if frappe.db.has_column("Maintenance Task", "start_date") else "mt.creation"
        end_date_field_mt = "mt.completion_date"
        if not frappe.db.has_column("Maintenance Task", "completion_date") and frappe.db.has_column("Maintenance Task", "expected_completion_date"):
            end_date_field_mt = "mt.expected_completion_date"
        elif not frappe.db.has_column("Maintenance Task", "completion_date"):
             # If neither completion_date nor expected_completion_date exists, this query part might fail or return nulls for end_date
             # For simplicity, we'll proceed assuming one of them exists, or the query will just not find matches for date range on end_date
             # A robust solution would handle this by perhaps not filtering on end_date if the field is missing.
             pass


        maintenance_tasks_query = f"""
            SELECT 
                mt.item_code, 
                mt.serial_no,
                'Maintenance Task' as event_type,
                mt.name as reference_name,
                'Maintenance Task' as reference_doctype,
                mt.status,
                {start_date_field_mt} as start_date,
                {end_date_field_mt} as end_date, 
                NULL as customer
            FROM `tabMaintenance Task` mt
            {item_join_mt}
            WHERE mt.docstatus = 1
              {mt_company_filter}
              AND mt.status NOT IN ('Cancelled', 'Completed') 
              AND {start_date_field_mt} <= %(to_date)s
              AND {end_date_field_mt} >= %(from_date)s
              {mt_conditions}
        """
        if frappe.db.has_column("Maintenance Task", "start_date") and \
           (frappe.db.has_column("Maintenance Task", "completion_date") or frappe.db.has_column("Maintenance Task", "expected_completion_date")):
            maintenance_data = frappe.db.sql(maintenance_tasks_query, current_sql_params_mt, as_dict=True)
            data.extend(maintenance_data)
            
    return data
