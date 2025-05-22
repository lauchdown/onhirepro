# Copyright (c) 2025, OnHire Pro and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from frappe.utils import now_datetime, get_datetime

class StockReconciliationLog(Document):
    def validate(self):
        """Validate the reconciliation log"""
        if not self.details:
            frappe.throw("Discrepancy details are required")
        
        # Set the log_datetime if not provided
        if not self.log_datetime:
            self.log_datetime = now_datetime()
    
    def resolve(self, resolution_notes, resolved_by=None):
        """Mark the discrepancy as resolved"""
        if not resolution_notes:
            frappe.throw("Resolution notes are required")
        
        self.status = "Resolved"
        self.resolution_notes = resolution_notes
        self.resolved_by = resolved_by or frappe.session.user
        self.save()
