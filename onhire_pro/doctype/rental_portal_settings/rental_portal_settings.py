import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url

class RentalPortalSettings(Document):
    def validate(self):
        self.validate_booking_days()
        self.validate_rate_multipliers()
        self.setup_default_booking_form_fields()
    
    def validate_booking_days(self):
        """Validate booking day constraints"""
        if self.min_booking_days <= 0:
            frappe.throw(_("Minimum Booking Days must be greater than 0"))
        
        if self.max_booking_days < self.min_booking_days:
            frappe.throw(_("Maximum Booking Days must be greater than or equal to Minimum Booking Days"))
        
        if self.advance_booking_days < 0:
            frappe.throw(_("Advance Booking Days must be greater than or equal to 0"))
    
    def validate_rate_multipliers(self):
        """Validate rate multipliers"""
        if self.weekly_rate_multiplier <= 0:
            frappe.throw(_("Weekly Rate Multiplier must be greater than 0"))
        
        if self.monthly_rate_multiplier <= 0:
            frappe.throw(_("Monthly Rate Multiplier must be greater than 0"))
        
        if self.monthly_rate_multiplier <= self.weekly_rate_multiplier:
            frappe.msgprint(_("Monthly Rate Multiplier should typically be greater than Weekly Rate Multiplier"))
    
    def setup_default_booking_form_fields(self):
        """Set up default booking form fields if not already defined"""
        # Contact Fields
        if not self.contact_fields:
            self.setup_default_contact_fields()
        
        # Job Reference Fields
        if not self.job_reference_fields:
            self.setup_default_job_reference_fields()
        
        # Project Detail Fields
        if not self.project_detail_fields:
            self.setup_default_project_detail_fields()
        
        # Delivery Fields
        if not self.delivery_fields:
            self.setup_default_delivery_fields()
    
    def setup_default_contact_fields(self):
        """Set up default contact fields"""
        contact_fields = [
            {"field_name": "contact_name", "field_label": "Contact Name", "field_type": "Data", "required": 1, "enabled": 1},
            {"field_name": "contact_email", "field_label": "Contact Email", "field_type": "Email", "required": 1, "enabled": 1},
            {"field_name": "contact_phone", "field_label": "Contact Phone", "field_type": "Phone", "required": 1, "enabled": 1},
            {"field_name": "alternate_contact_name", "field_label": "Alternate Contact Name", "field_type": "Data", "required": 0, "enabled": 1},
            {"field_name": "alternate_contact_phone", "field_label": "Alternate Contact Phone", "field_type": "Phone", "required": 0, "enabled": 1}
        ]
        
        for field in contact_fields:
            self.append("contact_fields", field)
    
    def setup_default_job_reference_fields(self):
        """Set up default job reference fields"""
        job_reference_fields = [
            {"field_name": "job_reference_number", "field_label": "Job Reference Number", "field_type": "Data", "required": 0, "enabled": 1},
            {"field_name": "project_name", "field_label": "Project Name", "field_type": "Data", "required": 0, "enabled": 1},
            {"field_name": "department", "field_label": "Department", "field_type": "Data", "required": 0, "enabled": 1}
        ]
        
        for field in job_reference_fields:
            self.append("job_reference_fields", field)
    
    def setup_default_project_detail_fields(self):
        """Set up default project detail fields"""
        project_detail_fields = [
            {"field_name": "project_description", "field_label": "Project Description", "field_type": "Text", "required": 0, "enabled": 1},
            {"field_name": "project_start_date", "field_label": "Project Start Date", "field_type": "Date", "required": 0, "enabled": 1},
            {"field_name": "project_end_date", "field_label": "Project End Date", "field_type": "Date", "required": 0, "enabled": 1},
            {"field_name": "special_requirements", "field_label": "Special Requirements", "field_type": "Text", "required": 0, "enabled": 1}
        ]
        
        for field in project_detail_fields:
            self.append("project_detail_fields", field)
    
    def setup_default_delivery_fields(self):
        """Set up default delivery fields"""
        delivery_fields = [
            {"field_name": "delivery_address", "field_label": "Delivery Address", "field_type": "Text", "required": 1, "enabled": 1},
            {"field_name": "delivery_date", "field_label": "Preferred Delivery Date", "field_type": "Date", "required": 0, "enabled": 1},
            {"field_name": "delivery_time", "field_label": "Preferred Delivery Time", "field_type": "Select", "required": 0, "enabled": 1, "default_value": "Morning"},
            {"field_name": "delivery_instructions", "field_label": "Delivery Instructions", "field_type": "Text", "required": 0, "enabled": 1},
            {"field_name": "site_contact_name", "field_label": "Site Contact Name", "field_type": "Data", "required": 0, "enabled": 1},
            {"field_name": "site_contact_phone", "field_label": "Site Contact Phone", "field_type": "Phone", "required": 0, "enabled": 1}
        ]
        
        for field in delivery_fields:
            self.append("delivery_fields", field)

def get_rental_portal_settings():
    """Get rental portal settings"""
    return frappe.get_single("Rental Portal Settings")

def get_portal_navigation_items():
    """Get portal navigation items based on settings"""
    settings = get_rental_portal_settings()
    
    nav_items = []
    
    # Home
    nav_items.append({
        "label": "Home",
        "url": "/",
        "icon": "fa-home"
    })
    
    # Rental Catalog
    if settings.enable_rental_catalog:
        nav_items.append({
            "label": "Rental Catalog",
            "url": "/rental-catalog",
            "icon": "fa-box-open"
        })
    
    # Sales Catalog
    if settings.enable_sales_catalog:
        nav_items.append({
            "label": "Sales Catalog",
            "url": "/sales-catalog",
            "icon": "fa-shopping-cart"
        })
    
    # Dashboard
    if settings.show_dashboard_link:
        nav_items.append({
            "label": "Dashboard",
            "url": "/my-bookings-dashboard",
            "icon": "fa-tachometer-alt"
        })
    
    # My Bookings
    if settings.show_bookings_link:
        nav_items.append({
            "label": "My Bookings",
            "url": "/my-bookings",
            "icon": "fa-clipboard-list"
        })
    
    # My Rentals
    if settings.show_rentals_link:
        nav_items.append({
            "label": "My Rentals",
            "url": "/my-rentals",
            "icon": "fa-truck-loading"
        })
    
    # Calendar
    if settings.show_calendar_link:
        nav_items.append({
            "label": "Calendar",
            "url": "/calendar-view",
            "icon": "fa-calendar-alt"
        })
    
    # Documents
    if settings.show_documents_link and settings.enable_document_access:
        nav_items.append({
            "label": "Documents",
            "url": "/my-documents",
            "icon": "fa-file-alt"
        })
    
    # Profile
    if settings.show_profile_link:
        nav_items.append({
            "label": "My Profile",
            "url": "/me",
            "icon": "fa-user"
        })
    
    return nav_items

def get_portal_branding():
    """Get portal branding settings"""
    settings = get_rental_portal_settings()
    
    branding = {
        "title": settings.portal_title,
        "description": settings.portal_description,
        "primary_color": settings.primary_color,
        "secondary_color": settings.secondary_color,
        "accent_color": settings.accent_color,
        "logo_url": settings.logo and get_url(settings.logo) or None,
        "favicon_url": settings.favicon and get_url(settings.favicon) or None,
        "custom_css": settings.custom_css
    }
    
    return branding
