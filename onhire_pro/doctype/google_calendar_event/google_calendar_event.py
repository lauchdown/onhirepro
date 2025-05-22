# Copyright (c) 2025, OnHire Pro and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class GoogleCalendarEvent(Document):
    def validate(self):
        """Validate Google Calendar Event mapping"""
        # Ensure reference document exists
        if not frappe.db.exists(self.reference_doctype, self.reference_name):
            frappe.throw(f"{self.reference_doctype} {self.reference_name} does not exist")
        
        # Ensure Google Event ID is unique
        if frappe.db.exists("Google Calendar Event", {"google_event_id": self.google_event_id, "name": ["!=", self.name]}):
            frappe.throw(f"Google Event ID {self.google_event_id} is already mapped to another document")
    
    def update_sync_status(self, status, sync_datetime=None):
        """Update sync status and timestamp"""
        self.sync_status = status
        if sync_datetime:
            self.last_sync_datetime = sync_datetime
        else:
            self.last_sync_datetime = frappe.utils.now_datetime()
        self.save()
