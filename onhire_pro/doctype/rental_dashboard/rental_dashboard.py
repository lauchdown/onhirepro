import frappe
from frappe.model.document import Document

class RentalDashboard(Document):
    def validate(self):
        self.validate_default_dashboard()
    
    def validate_default_dashboard(self):
        """Ensure only one dashboard is set as default"""
        if self.is_default:
            # Check if any other dashboard is set as default
            default_dashboards = frappe.get_all(
                "Rental Dashboard",
                filters={"is_default": 1, "name": ["!=", self.name]}
            )
            
            if default_dashboards:
                # Unset default for other dashboards
                for dashboard in default_dashboards:
                    frappe.db.set_value("Rental Dashboard", dashboard.name, "is_default", 0)
                    
    def on_update(self):
        """Actions to take when dashboard is updated"""
        # Clear cache to ensure updated dashboard is shown
        frappe.cache().delete_key("rental_dashboard")
