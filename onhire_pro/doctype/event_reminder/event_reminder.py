# Copyright (c) 2025, OnHire Pro and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, add_to_date, cint

class EventReminder(Document):
    def validate(self):
        self.validate_recipients()
        self.calculate_reminder_datetime()
    
    def validate_recipients(self):
        """Ensure at least one recipient is specified"""
        if not self.recipient_user and not self.recipient_contact and not self.recipient_email:
            frappe.throw("At least one recipient (User, Contact, or Email) must be specified")
        
        # If recipient_contact is specified, fetch email if recipient_email is not provided
        if self.recipient_contact and not self.recipient_email:
            email = frappe.db.get_value("Contact", self.recipient_contact, "email_id")
            if email:
                self.recipient_email = email
    
    def calculate_reminder_datetime(self):
        """Calculate the reminder datetime based on reference document and lead time"""
        if not self.reference_doctype or not self.reference_name:
            return
        
        # Get the start date/time from the reference document
        if self.reference_doctype == "Rental Event":
            start_date = frappe.db.get_value("Rental Event", self.reference_name, "start_date")
        elif self.reference_doctype == "Rental Job":
            start_date = frappe.db.get_value("Rental Job", self.reference_name, "scheduled_dispatch_date")
        elif self.reference_doctype == "Maintenance Task":
            start_date = frappe.db.get_value("Maintenance Task", self.reference_name, "scheduled_date")
        else:
            return
        
        if not start_date:
            return
        
        # Calculate reminder datetime based on lead time
        if self.lead_time_unit == "Minutes":
            self.reminder_datetime = add_to_date(start_date, minutes=-cint(self.lead_time_value))
        elif self.lead_time_unit == "Hours":
            self.reminder_datetime = add_to_date(start_date, hours=-cint(self.lead_time_value))
        elif self.lead_time_unit == "Days":
            self.reminder_datetime = add_to_date(start_date, days=-cint(self.lead_time_value))
