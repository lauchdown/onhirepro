# Copyright (c) 2025, OnHire Pro and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

class RentalJob(Document):
    def validate(self):
        self.validate_dates()
        self.set_status_based_on_dates()

    def validate_dates(self):
        if self.scheduled_return_date and self.scheduled_dispatch_date and get_datetime(self.scheduled_return_date) < get_datetime(self.scheduled_dispatch_date):
            frappe.throw("Scheduled Return Date cannot be before Scheduled Dispatch Date")
        if self.actual_return_date and self.actual_dispatch_date and get_datetime(self.actual_return_date) < get_datetime(self.actual_dispatch_date):
            frappe.throw("Actual Return Date cannot be before Actual Dispatch Date")

    def set_status_based_on_dates(self):
        # This is a placeholder for more complex status logic based on item dispatch/return
        if self.actual_dispatch_date and not self.actual_return_date:
            if self.job_status not in ["Dispatched", "Partially Returned"]:
                # self.job_status = "Dispatched" # This should be set by other processes like Delivery Note
                pass 
        elif self.actual_return_date:
            if self.job_status not in ["Returned", "Pending Condition Assessment", "Condition Assessment Complete", "Pending Invoicing", "Invoiced", "Completed"]:
                # self.job_status = "Returned" # This should be set by other processes like Stock Entry
                pass

    def on_submit(self):
        # Placeholder for logic on submit, e.g., creating rental events if not already created
        pass

    def on_cancel(self):
        # Placeholder for logic on cancel, e.g., cancelling related rental events or reservations
        pass

    # Method to be called when items are dispatched
    def on_dispatch(self):
        self.actual_dispatch_date = now_datetime()
        # Potentially update status or trigger other workflows
        self.save()

    # Method to be called when items are returned
    def on_return(self):
        self.actual_return_date = now_datetime()
        # Potentially update status or trigger other workflows
        self.save()
