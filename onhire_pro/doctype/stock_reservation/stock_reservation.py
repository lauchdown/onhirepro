# Copyright (c) 2025, OnHire Pro and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from frappe.utils import now_datetime, get_datetime, add_to_date

class StockReservation(Document):
    def validate(self):
        self.validate_dates()
        self.validate_item_availability()
        
    def validate_dates(self):
        """Ensure to_date is after from_date"""
        if self.from_date and self.to_date:
            from_date = get_datetime(self.from_date)
            to_date = get_datetime(self.to_date)
            
            if to_date <= from_date:
                frappe.throw("To Date must be after From Date")
    
    def validate_item_availability(self):
        """Check if the item is available for reservation during the specified period"""
        if self.serial_no:
            self.validate_serialized_item()
        else:
            self.validate_non_serialized_item()
    
    def validate_serialized_item(self):
        """Check if a serialized item is already reserved during the requested period"""
        # Skip validation if this is an update of an existing reservation
        if not self.is_new():
            return
            
        conflicts = frappe.db.sql("""
            SELECT sr.name, sr.reference_doctype, sr.reference_name, sr.from_date, sr.to_date
            FROM `tabStock Reservation` sr
            WHERE 
                sr.serial_no = %s
                AND sr.name != %s
                AND sr.docstatus = 1
                AND sr.status IN ('Reserved', 'In Use')
                AND (
                    (sr.from_date <= %s AND sr.to_date >= %s)
                    OR (sr.from_date <= %s AND sr.to_date >= %s)
                    OR (sr.from_date >= %s AND sr.to_date <= %s)
                )
        """, (
            self.serial_no, 
            self.name or "New Stock Reservation",
            self.to_date, self.from_date,
            self.from_date, self.from_date,
            self.from_date, self.to_date
        ), as_dict=1)
        
        if conflicts:
            conflict = conflicts[0]
            frappe.throw(f"Serial No {self.serial_no} is already reserved in {conflict.reference_doctype} {conflict.reference_name} from {conflict.from_date} to {conflict.to_date}")
    
    def validate_non_serialized_item(self):
        """Check if enough quantity of a non-serialized item is available during the requested period"""
        # Skip validation if this is an update of an existing reservation
        if not self.is_new():
            return
            
        # Get total quantity of this item reserved during the period
        reserved_qty = frappe.db.sql("""
            SELECT SUM(sr.qty) as total_qty
            FROM `tabStock Reservation` sr
            WHERE 
                sr.item_code = %s
                AND sr.serial_no IS NULL
                AND sr.name != %s
                AND sr.docstatus = 1
                AND sr.status IN ('Reserved', 'In Use')
                AND (
                    (sr.from_date <= %s AND sr.to_date >= %s)
                    OR (sr.from_date <= %s AND sr.to_date >= %s)
                    OR (sr.from_date >= %s AND sr.to_date <= %s)
                )
        """, (
            self.item_code, 
            self.name or "New Stock Reservation",
            self.to_date, self.from_date,
            self.from_date, self.from_date,
            self.from_date, self.to_date
        ), as_dict=1)
        
        reserved_qty = reserved_qty[0].total_qty or 0
        
        # Get available quantity from stock
        available_qty = self.get_available_qty()
        
        if (reserved_qty + self.qty) > available_qty:
            frappe.throw(f"Not enough quantity available for {self.item_code}. Requested: {self.qty}, Available: {available_qty - reserved_qty}")
    
    def get_available_qty(self):
        """Get available quantity of an item from stock"""
        # This is a simplified version - in a real implementation, 
        # you would query the actual stock ledger or bin
        available_qty = frappe.db.sql("""
            SELECT SUM(actual_qty) as qty
            FROM `tabBin`
            WHERE item_code = %s
        """, (self.item_code), as_dict=1)
        
        return available_qty[0].qty or 0
    
    def on_submit(self):
        """Update item status when reservation is submitted"""
        if self.serial_no:
            # Update Serial No status
            frappe.db.set_value("Serial No", self.serial_no, "reservation_status", "Reserved")
            frappe.db.set_value("Serial No", self.serial_no, "reserved_for", f"{self.reference_doctype}: {self.reference_name}")
    
    def on_cancel(self):
        """Update item status when reservation is cancelled"""
        if self.serial_no:
            # Update Serial No status
            frappe.db.set_value("Serial No", self.serial_no, "reservation_status", "Available")
            frappe.db.set_value("Serial No", self.serial_no, "reserved_for", None)
    
    def mark_as_in_use(self):
        """Mark the reservation as in use when the item is dispatched"""
        if self.status == "Reserved":
            self.status = "In Use"
            self.save()
            
            if self.serial_no:
                # Update Serial No status
                frappe.db.set_value("Serial No", self.serial_no, "reservation_status", "In Use")
    
    def mark_as_returned(self):
        """Mark the reservation as completed when the item is returned"""
        if self.status in ["Reserved", "In Use"]:
            self.status = "Completed"
            self.save()
            
            if self.serial_no:
                # Update Serial No status
                frappe.db.set_value("Serial No", self.serial_no, "reservation_status", "Available")
                frappe.db.set_value("Serial No", self.serial_no, "reserved_for", None)
    
    def log_override(self, reason, user):
        """Log an override of this reservation"""
        override_log = frappe.new_doc("Stock Reservation Override Log")
        override_log.reservation = self.name
        override_log.item_code = self.item_code
        override_log.serial_no = self.serial_no
        override_log.override_date = now_datetime()
        override_log.override_by = user
        override_log.reason = reason
        override_log.reference_doctype = self.reference_doctype
        override_log.reference_name = self.reference_name
        override_log.insert()
