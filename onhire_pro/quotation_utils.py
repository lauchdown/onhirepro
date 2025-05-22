import frappe
from frappe.utils import flt, get_datetime
from frappe import _

def validate_item_availability_for_quotation(quotation_doc):
    """Validate item availability for all items in a quotation."""
    if not quotation_doc.get("is_rental_quotation") or not quotation_doc.items:
        return

    for item in quotation_doc.items:
        if item.item_type == "Rental":
            if not item.rental_item_start_date or not item.rental_item_end_date:
                frappe.throw(_("Rental Start Date and End Date are required for rental item {0}").format(item.item_code))
            
            check_single_item_availability(
                item.item_code,
                item.qty,
                item.rental_item_start_date,
                item.rental_item_end_date,
                item.serial_no,
                quotation_doc.name
            )

def check_single_item_availability(item_code, qty, start_date, end_date, serial_no=None, exclude_docname=None):
    """Check availability for a single item for a given period."""
    start_datetime = get_datetime(start_date)
    end_datetime = get_datetime(end_date)

    if serial_no:
        # Check for serialized item conflicts
        conflicts = frappe.db.sql("""
            SELECT sr.name, sr.reference_doctype, sr.reference_name
            FROM `tabStock Reservation` sr
            WHERE sr.serial_no = %(serial_no)s
                AND sr.docstatus = 1
                AND sr.status IN (
                    'Reserved', 'In Use'
                )
                AND sr.name != %(exclude_docname)s
                AND (
                    (sr.from_date < %(end_date)s AND sr.to_date > %(start_date)s)
                )
        """, {
            "serial_no": serial_no,
            "start_date": start_datetime,
            "end_date": end_datetime,
            "exclude_docname": exclude_docname or ""
        }, as_dict=1)
        if conflicts:
            conflict = conflicts[0]
            frappe.throw(
                _("Serial No {0} for item {1} is already reserved or in use in {2} {3} during the selected period.").format(
                    serial_no, item_code, conflict.reference_doctype, conflict.reference_name
                )
            )
    else:
        # Check for non-serialized item conflicts
        # Get total quantity of this item reserved during the period
        overlapping_reservations = frappe.db.sql("""
            SELECT SUM(sr.qty) as reserved_qty
            FROM `tabStock Reservation` sr
            WHERE sr.item_code = %(item_code)s
                AND sr.serial_no IS NULL
                AND sr.docstatus = 1
                AND sr.status IN (
                    'Reserved', 'In Use'
                )
                AND sr.name != %(exclude_docname)s
                AND (
                    (sr.from_date < %(end_date)s AND sr.to_date > %(start_date)s)
                )
        """, {
            "item_code": item_code,
            "start_date": start_datetime,
            "end_date": end_datetime,
            "exclude_docname": exclude_docname or ""
        }, as_dict=1)
        
        reserved_qty = overlapping_reservations[0].reserved_qty if overlapping_reservations and overlapping_reservations[0].reserved_qty else 0
        
        # Get available quantity from stock (simplified, assumes a default warehouse or uses ERPNext's logic)
        # In a real scenario, warehouse would be a parameter
        actual_qty_at_warehouse = frappe.db.get_value(
            "Bin",
            {"item_code": item_code, "warehouse": quotation_doc.set_warehouse}, # Assuming set_warehouse is on Quotation
            "actual_qty"
        ) or 0
        
        projected_qty = actual_qty_at_warehouse - reserved_qty

        if flt(qty) > projected_qty:
            frappe.throw(
                _("Not enough quantity available for item {0}. Requested: {1}, Available (considering other reservations): {2}").format(
                    item_code, qty, projected_qty
                )
            )

def create_reservations_for_quotation(quotation_doc):
    """Create stock reservations for rental items in an approved quotation."""
    if not quotation_doc.get("is_rental_quotation") or not quotation_doc.items:
        return

    if quotation_doc.workflow_state != "Approved": # Or your specific approved state
        return

    for item in quotation_doc.items:
        if item.item_type == "Rental":
            try:
                reservation = frappe.new_doc("Stock Reservation")
                reservation.item_code = item.item_code
                reservation.qty = item.qty
                reservation.serial_no = item.serial_no
                reservation.from_date = item.rental_item_start_date
                reservation.to_date = item.rental_item_end_date
                reservation.reference_doctype = "Quotation"
                reservation.reference_name = quotation_doc.name
                reservation.status = "Reserved"
                # Add warehouse if applicable, e.g., from quotation_doc.set_warehouse
                # reservation.warehouse = quotation_doc.set_warehouse 
                reservation.insert(ignore_permissions=True) # Use with caution
                frappe.msgprint(_("Reservation created for item {0}").format(item.item_code))
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), _("Error creating reservation for item {0} in Quotation {1}").format(item.item_code, quotation_doc.name))
                frappe.throw(_("Could not create reservation for item {0}: {1}").format(item.item_code, str(e)))

# Hooks for Quotation DocType

# This would typically go into hooks.py of your app
# For now, imagine these are connected:
# doc_events = {
# "Quotation": {
# "validate": "onhire_pro.onhire_pro.quotation_utils.validate_item_availability_for_quotation",
# "on_update_after_submit": "onhire_pro.onhire_pro.quotation_utils.handle_quotation_approval_for_reservation"
# }
# }

# We'll need a function to be called on workflow state change to "Approved"
def handle_quotation_approval_for_reservation(doc, method):
    if doc.workflow_state == "Approved": # Replace with your actual approved state name
        create_reservations_for_quotation(doc)
