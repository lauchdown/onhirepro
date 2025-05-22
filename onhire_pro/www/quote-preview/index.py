import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint, nowdate, get_datetime, time_diff_in_hours, flt
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for quote preview page"""
    
    # Get rental portal settings
    settings = get_rental_portal_settings()
    
    # Check if portal is enabled
    if not settings.enable_rental_portal:
        frappe.throw(_("Customer Portal is not enabled"), frappe.PermissionError)
    
    # Add settings to context
    context.settings = settings
    
    # Add navigation items to context
    context.nav_items = get_portal_navigation_items()
    
    # Set breadcrumbs
    context.breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "Cart", "url": "/cart"},
        {"label": "Project Details", "url": "/project-details"},
        {"label": "Quote Preview", "url": "/quote-preview"}
    ]
    
    # Get booking ID from URL
    booking_id = frappe.form_dict.get('booking_id')
    
    if not booking_id:
        frappe.throw(_("No booking ID provided"))
    
    # Get booking details
    booking = get_booking_details(booking_id)
    context.booking = booking
    context.booking_id = booking_id
    
    # Generate quote number
    context.quote_number = f"Q-{frappe.utils.now().strftime('%Y%m%d')}-{booking_id[-6:]}"
    
    # Get customer details
    context.customer = get_customer_details()
    
    # Get project details
    context.project_details = get_project_details(booking_id)
    
    # Get terms and conditions
    context.terms_and_conditions = get_terms_and_conditions()
    
    return context

def get_booking_details(booking_id):
    """Get booking details for the given booking ID"""
    
    # Get booking from session or database
    booking_data = frappe.cache().get_value(f"booking_draft_{booking_id}")
    
    if not booking_data:
        frappe.throw(_("Booking not found or session expired"))
    
    # Calculate booking duration
    start_date = getdate(booking_data.get("start_date"))
    end_date = getdate(booking_data.get("end_date"))
    duration = (end_date - start_date).days + 1
    
    # Get items
    items = booking_data.get("items", [])
    total_items = sum(item.get("qty", 0) for item in items)
    
    # Calculate totals
    subtotal = sum(item.get("amount", 0) for item in items)
    
    # Get tax rate from settings
    settings = get_rental_portal_settings()
    tax_rate = flt(settings.default_tax_rate)
    
    # Calculate discount if applicable
    discount_percent = flt(booking_data.get("discount_percent", 0))
    discount_amount = flt(subtotal * discount_percent / 100)
    
    # Calculate delivery fee if applicable
    delivery_fee = 0
    if booking_data.get("delivery_method") == "delivery":
        delivery_fee = flt(booking_data.get("delivery_fee", 0))
    
    # Calculate tax and total
    tax_amount = flt((subtotal - discount_amount) * tax_rate / 100)
    total = flt(subtotal - discount_amount + tax_amount + delivery_fee)
    
    # Prepare booking summary
    booking_summary = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "duration": duration,
        "total_items": total_items,
        "items": items,
        "subtotal": subtotal,
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "delivery_method": booking_data.get("delivery_method", "pickup"),
        "delivery_fee": delivery_fee,
        "total": total
    }
    
    return booking_summary

def get_customer_details():
    """Get customer details for the current user"""
    
    # Get customer linked to the current user
    customer_name = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    
    if not customer_name:
        frappe.throw(_("No customer account found for your user. Please contact support."))
    
    # Get customer details
    customer = frappe.get_doc("Customer", customer_name)
    
    # Get contact details
    contact = frappe.db.get_value("Contact", 
                                 {"email_id": frappe.session.user}, 
                                 ["name", "first_name", "last_name", "phone", "mobile_no"], 
                                 as_dict=True)
    
    # Prepare customer details
    customer_details = {
        "name": customer.customer_name,
        "email": frappe.session.user,
        "phone": contact.phone or contact.mobile_no if contact else "",
        "address": get_customer_primary_address(customer_name)
    }
    
    return customer_details

def get_customer_primary_address(customer_name):
    """Get primary address for the customer"""
    
    address_name = frappe.db.get_value("Dynamic Link", 
                                      {"link_doctype": "Customer", "link_name": customer_name, 
                                       "parenttype": "Address"}, 
                                      "parent")
    
    if not address_name:
        return ""
    
    address = frappe.get_doc("Address", address_name)
    
    address_parts = [
        address.address_line1,
        address.address_line2,
        address.city,
        address.state,
        address.pincode,
        address.country
    ]
    
    # Filter out empty parts and join with commas
    return ", ".join([part for part in address_parts if part])

def get_project_details(booking_id):
    """Get project details for the booking"""
    
    # Get project details from session
    project_data = frappe.cache().get_value(f"project_details_{booking_id}")
    
    if not project_data:
        return []
    
    # Format project details for display
    project_details = []
    
    for key, value in project_data.items():
        if key not in ["csrf_token", "booking_id"] and value:
            # Convert field_name to Field Label format
            label = " ".join(word.capitalize() for word in key.split("_"))
            project_details.append({
                "label": label,
                "value": value
            })
    
    return project_details

def get_terms_and_conditions():
    """Get terms and conditions for bookings"""
    
    # Get terms from settings or use default
    settings = get_rental_portal_settings()
    company = settings.company
    
    if company:
        terms = frappe.db.get_value("Terms and Conditions", 
                                   {"selling": 1, "disabled": 0, "company": company}, 
                                   "terms")
        
        if terms:
            return terms
    
    # Default terms if not found
    return """
    <ol>
        <li>All rental items remain the property of the company.</li>
        <li>Customer is responsible for the proper use and care of rental items.</li>
        <li>Damage beyond normal wear and tear will be charged to the customer.</li>
        <li>Late returns will incur additional daily charges at the standard rate.</li>
        <li>Cancellation policy: 48 hours notice required for full refund.</li>
        <li>Delivery fees are non-refundable once delivery has been scheduled.</li>
        <li>Payment terms: 50% deposit required at booking, balance due at delivery/pickup.</li>
        <li>All prices are subject to applicable taxes.</li>
    </ol>
    """
