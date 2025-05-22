import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for cart page"""
    
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
        {"label": "Cart", "url": "/cart"}
    ]
    
    # Get cart items
    context.cart = get_cart_items()
    
    return context

def get_cart_items():
    """Get current cart items for the user"""
    
    # Check if user is logged in
    if not frappe.session.user or frappe.session.user == 'Guest':
        return {"items": [], "total": 0}
    
    # Get cart from session or create new
    cart = frappe.cache().hget("shopping_cart", frappe.session.user)
    if not cart:
        cart = {
            "items": [],
            "total": 0
        }
    
    return cart
