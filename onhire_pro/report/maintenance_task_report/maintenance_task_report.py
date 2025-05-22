# Project/onhire_pro/onhire_pro/report/maintenance_task_report/maintenance_task_report.py
import frappe
from frappe import _
from frappe.utils import getdate, date_diff, flt, cint, get_datetime, nowdate

def execute(filters=None):
    # Check if Maintenance Task DocType exists
    if not frappe.db.exists("DocType", "Maintenance Task"):
        frappe.msgprint(_("DocType 'Maintenance Task' not found. Please ensure it is installed/created for this report."), indicator="orange", alert=True)
        return [], [], None, None, None

    columns, report_summary_columns = get_columns(filters)
    data = get_data(filters, report_summary_columns) # Pass summary columns to potentially populate summary data
    
    report_summary = None
    if data: # Calculate summary if data exists
        avg_turnaround = calculate_summary_avg_turnaround(data)
        report_summary = [
            {"label": _("Total Tasks Displayed"), "value": len(data), "indicator": "Blue"},
            {"label": _("Average Turnaround (Completed, Days)"), "value": avg_turnaround, "indicator": "Green"}
        ]
        
    return columns, data, None, None, report_summary

def get_columns(filters):
    columns = [
        {"label": _("Task ID"), "fieldname": "name", "fieldtype": "Link", "options": "Maintenance Task", "width": 120},
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": _("Serial No"), "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial No", "width": 120},
        {"label": _("Task Type"), "fieldname": "maintenance_type", "fieldtype": "Data", "width": 150}, # Assuming 'maintenance_type' field
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": _("Assigned To"), "fieldname": "assigned_to", "fieldtype": "Link", "options": "User", "width": 120},
        {"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Datetime", "width": 150},
        {"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 120}, # Assuming 'due_date' field
        {"label": _("Completion Date"), "fieldname": "completion_date", "fieldtype": "Datetime", "width": 150},
        {"label": _("Turnaround Time (Days)"), "fieldname": "turnaround_time", "fieldtype": "Float", "width": 160},
        {"label": _("Overdue Status"), "fieldname": "overdue_status", "fieldtype": "Data", "width": 120},
        # {"label": _("SLA Met"), "fieldname": "sla_met", "fieldtype": "Data", "width": 100} # SLA logic can be complex
    ]
    report_summary_columns = ["turnaround_time"] # For summary calculation
    return columns, report_summary_columns

def get_data(filters, report_summary_columns):
    sql_filters = {"docstatus": 1} # Submitted tasks
    # sql_params = {} # Not needed for frappe.get_all with dict filters

    if filters.get("company") and frappe.db.has_column("Maintenance Task", "company"):
        sql_filters["company"] = filters.get("company")
    
    date_field_to_filter = "start_date" if frappe.db.has_column("Maintenance Task", "start_date") else "creation"

    # Date filtering logic
    from_date_filter = filters.get("from_date")
    to_date_filter = filters.get("to_date")

    if from_date_filter and to_date_filter:
        sql_filters[date_field_to_filter] = ["between", [from_date_filter, to_date_filter]]
    elif from_date_filter:
        sql_filters[date_field_to_filter] = [">=", from_date_filter]
    elif to_date_filter:
        sql_filters[date_field_to_filter] = ["<=", to_date_filter]


    if filters.get("status"):
        sql_filters["status"] = filters.get("status")
    if filters.get("item_code") and frappe.db.has_column("Maintenance Task", "item_code"):
        sql_filters["item_code"] = filters.get("item_code")
    if filters.get("serial_no") and frappe.db.has_column("Maintenance Task", "serial_no"):
        sql_filters["serial_no"] = filters.get("serial_no")
    if filters.get("assigned_to") and frappe.db.has_column("Maintenance Task", "assigned_to"):
        sql_filters["assigned_to"] = filters.get("assigned_to")
    if filters.get("maintenance_type") and frappe.db.has_column("Maintenance Task", "maintenance_type"):
        sql_filters["maintenance_type"] = filters.get("maintenance_type")

    fields_to_fetch = ["name", "status", "creation"]
    # Conditionally add fields if they exist in the DocType schema
    for field in ["item_code", "serial_no", "maintenance_type", "assigned_to", "start_date", "due_date", "completion_date"]:
        if frappe.db.has_column("Maintenance Task", field):
            fields_to_fetch.append(field)


    tasks = frappe.get_all("Maintenance Task", filters=sql_filters, fields=fields_to_fetch, order_by="creation desc")

    for task in tasks:
        start_dt = get_datetime(task.get("start_date") or task.creation)
        completion_dt = get_datetime(task.get("completion_date"))
        due_dt = getdate(task.get("due_date")) if task.get("due_date") else None


        if task.status == "Completed" and start_dt and completion_dt:
            task.turnaround_time = round((completion_dt - start_dt).total_seconds() / (3600 * 24), 2) # In days
        else:
            task.turnaround_time = None

        if task.status != "Completed" and due_dt and due_dt < nowdate():
            task.overdue_status = _("Overdue")
        elif task.status == "Completed":
            task.overdue_status = _("N/A (Completed)")
        else:
            task.overdue_status = _("Not Overdue")
            
        # Placeholder for SLA Met, requires SLA definition logic
        # task.sla_met = "N/A" 
            
    return tasks

def calculate_summary_avg_turnaround(data):
    total_turnaround = 0
    completed_tasks_count = 0
    for task in data:
        if task.get("status") == "Completed" and task.get("turnaround_time") is not None:
            total_turnaround += flt(task.turnaround_time)
            completed_tasks_count += 1
    
    return round(total_turnaround / completed_tasks_count, 2) if completed_tasks_count > 0 else 0.0
