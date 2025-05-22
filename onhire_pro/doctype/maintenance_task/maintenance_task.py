# Project/onhire_pro/onhire_pro/doctype/maintenance_task/maintenance_task.py
import frappe
from frappe.model.document import Document

class MaintenanceTask(Document):
    def validate(self):
        # Add any validation logic here if needed
        # For example, ensure start_date is before completion_date if both are set
        if self.start_date and self.completion_date and self.start_date > self.completion_date:
            frappe.throw("Completion Date cannot be before Start Date.")
        
        if self.item_code and not self.serial_no:
            item_doc = frappe.get_doc("Item", self.item_code)
            if item_doc.has_serial_no:
                frappe.msgprint(f"Item {self.item_code} is serialized. Please specify a Serial Number for the maintenance task if applicable.", indicator="orange")
        
        if self.serial_no and not self.item_code:
            item_code = frappe.db.get_value("Serial No", self.serial_no, "item_code")
            if item_code:
                self.item_code = item_code
            else:
                frappe.throw(f"Could not determine Item Code for Serial No {self.serial_no}")


    def on_submit(self):
        # Potentially update item/serial status if needed
        if self.status == "Completed":
            if self.serial_no:
                # Logic to update Serial No status, e.g., back to 'Available'
                # frappe.db.set_value("Serial No", self.serial_no, "status", "Available")
                pass
            elif self.item_code:
                # Logic for non-serialized item status update
                pass
        pass

    def on_cancel(self):
        # Revert any status changes made on submit if applicable
        pass
