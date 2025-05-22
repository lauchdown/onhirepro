import frappe
from frappe.model.document import Document

class ConditionAssessmentTemplate(Document):
    def validate(self):
        self.validate_checklist_items()
    
    def validate_checklist_items(self):
        """Ensure template has at least one checklist item"""
        if not self.checklist_items or len(self.checklist_items) == 0:
            frappe.throw("At least one checklist item is required for the template")
    
    def on_update(self):
        """Update linked assessments if template is modified"""
        # This is a placeholder for future implementation
        pass
