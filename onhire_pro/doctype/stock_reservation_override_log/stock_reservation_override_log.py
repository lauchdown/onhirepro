# Copyright (c) 2025, OnHire Pro and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from frappe.utils import now_datetime, get_datetime

class StockReservationOverrideLog(Document):
    def validate(self):
        """Validate the override log"""
        if not self.reason:
            frappe.throw("Reason for override is required")
        
        # Check if the referenced reservation exists
        if not frappe.db.exists("Stock Reservation", self.reservation):
            frappe.throw(f"Stock Reservation {self.reservation} does not exist")
        
        # Set the override date if not provided
        if not self.override_date:
            self.override_date = now_datetime()
        
        # Set the override_by if not provided
        if not self.override_by:
            self.override_by = frappe.session.user
