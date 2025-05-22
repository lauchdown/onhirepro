import frappe
from frappe.model.document import Document

class ConditionAssessment(Document):
    def validate(self):
        self.validate_photos()
        self.calculate_damage_charges()
    
    def validate_photos(self):
        """Validate that photos are attached based on assessment type and condition"""
        if self.assessment_type in ["Pre-Rental", "Post-Rental"] and not self.photos:
            frappe.throw("Photos are required for Pre-Rental and Post-Rental assessments")
        
        if self.overall_condition in ["Poor", "Damaged"] and not self.photos:
            frappe.throw("Photos are required when condition is Poor or Damaged")
    
    def calculate_damage_charges(self):
        """Calculate damage charges based on condition and damage rules"""
        if self.overall_condition in ["Poor", "Damaged"] and self.charge_customer:
            # Logic to calculate damage charges based on rules
            # This is a placeholder for the actual implementation
            pass
    
    def on_submit(self):
        """Actions to take when assessment is submitted"""
        # Update item status based on assessment
        if self.item_code and self.serial_no:
            item_status = "Available"
            if self.overall_condition in ["Poor", "Damaged"]:
                item_status = "Under Repair"
            
            # Update item status in the database
            frappe.db.set_value("Serial No", self.serial_no, "rental_status", item_status)
            
        # Create invoice for damage charges if applicable
        if self.charge_customer and self.damage_charges > 0 and self.customer:
            # Logic to create invoice for damage charges
            # This is a placeholder for the actual implementation
            pass
