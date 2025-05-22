import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for rental catalog page"""
    
    # Get rental portal settings
    settings = get_rental_portal_settings()
    
    # Check if rental catalog is enabled
    if not settings.enable_rental_portal or not settings.enable_rental_catalog_page:
        frappe.throw(_("Rental Catalog is not enabled"), frappe.PermissionError)
    
    # Add settings to context
    context.settings = settings
    
    # Add navigation items to context
    context.nav_items = get_portal_navigation_items()
    
    # Set breadcrumbs
    context.breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "Rental Catalog", "url": "/rental-catalog"}
    ]
    
    # Get filter parameters from URL
    start_date = frappe.form_dict.get('start_date')
    end_date = frappe.form_dict.get('end_date')
    category = frappe.form_dict.get('category')
    search = frappe.form_dict.get('search')
    
    # Set default dates if not provided
    if not start_date:
        start_date = frappe.utils.today()
    if not end_date:
        end_date = frappe.utils.add_days(start_date, 7)
    
    # Get all item categories (item groups)
    context.categories = frappe.get_all("Item Group", 
                                       filters={"show_in_website": 1},
                                       fields=["name"])
    
    # Build filters for items query
    filters = {
        "disabled": 0,
        "is_rental_item": 1,  # Custom field to identify rental items
        "show_in_website": 1
    }
    
    if category:
        filters["item_group"] = category
    
    # Get rental items
    items = frappe.get_all("Item", 
                          filters=filters,
                          fields=["name", "item_name", "item_group", 
                                 "description", "image", "standard_rate as rate",
                                 "rental_period_unit", "daily_rate", "weekly_rate", "monthly_rate"])
    
    # Apply sorting based on settings
    sort_order = settings.catalog_default_sort_order
    if sort_order == "Item Name (A-Z)":
        items.sort(key=lambda x: x.item_name)
    elif sort_order == "Item Name (Z-A)":
        items.sort(key=lambda x: x.item_name, reverse=True)
    elif sort_order == "Price (Low to High)":
        items.sort(key=lambda x: x.rate or 0)
    elif sort_order == "Price (High to Low)":
        items.sort(key=lambda x: x.rate or 0, reverse=True)
    # Most Popular would require additional data, default to name sort
    
    # Check availability for each item
    for item in items:
        item.available = check_item_availability(item.name, start_date, end_date)
        
        # Apply search filter if provided
        if search and search.lower() not in (item.item_name.lower() + " " + 
                                           (item.description or "").lower()):
            items.remove(item)
        
        # Calculate rates based on admin settings if not explicitly set
        if not item.daily_rate:
            item.daily_rate = item.rate
            
        if not item.weekly_rate and item.daily_rate:
            item.weekly_rate = item.daily_rate * settings.weekly_rate_multiplier
            
        if not item.monthly_rate and item.daily_rate:
            item.monthly_rate = item.daily_rate * settings.monthly_rate_multiplier
        
        # Calculate savings if enabled
        if settings.show_pricing_savings:
            item.weekly_savings = (item.daily_rate * 7) - item.weekly_rate if item.weekly_rate else 0
            item.monthly_savings = (item.daily_rate * 30) - item.monthly_rate if item.monthly_rate else 0
    
    # Handle out of stock items based on settings
    if settings.display_out_of_stock_items_policy == "Hide Out of Stock Items":
        items = [item for item in items if item.available]
    
    # Apply pagination
    items_per_page = settings.catalog_items_per_page or 12
    page = cint(frappe.form_dict.get('page', 1))
    start = (page - 1) * items_per_page
    end = start + items_per_page
    
    # Calculate pagination info
    total_items = len(items)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    context.pagination = {
        "current_page": page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
        "total_items": total_items,
        "showing_start": start + 1 if total_items > 0 else 0,
        "showing_end": min(end, total_items)
    }
    
    # Apply pagination to items
    context.items = items[start:end]
    
    # Pass filter values to template for form persistence
    context.filters = {
        "start_date": start_date,
        "end_date": end_date,
        "category": category,
        "search": search
    }
    
    return context

def check_item_availability(item_code, start_date, end_date):
    """Check if item is available for the given date range"""
    
    # Convert to datetime objects
    start_date = getdate(start_date)
    end_date = getdate(end_date)
    
    # Get total quantity of this item
    total_qty = frappe.db.get_value("Bin", 
                                   {"item_code": item_code, "warehouse": frappe.db.get_single_value("Stock Settings", "default_warehouse")},
                                   "actual_qty") or 0
    
    # If serialized item, check each serial number
    is_serialized = frappe.db.get_value("Item", item_code, "has_serial_no")
    
    if is_serialized:
        # Get all serial numbers for this item
        serial_nos = frappe.get_all("Serial No", 
                                   filters={"item_code": item_code, "status": "Active"},
                                   fields=["name"])
        
        # Check each serial number for reservations
        available_serial_nos = []
        for sn in serial_nos:
            # Check if serial number is reserved during the requested period
            reserved = frappe.db.sql("""
                SELECT name FROM `tabStock Reservation`
                WHERE serial_no = %s
                AND docstatus = 1
                AND status IN ('Reserved', 'In Use')
                AND (
                    (from_date <= %s AND to_date >= %s)
                    OR (from_date <= %s AND to_date >= %s)
                    OR (from_date >= %s AND to_date <= %s)
                )
            """, (sn.name, end_date, start_date, start_date, start_date, start_date, end_date))
            
            if not reserved:
                available_serial_nos.append(sn.name)
        
        # Item is available if at least one serial number is available
        return len(available_serial_nos) > 0
    else:
        # For non-serialized items, check total reserved quantity
        reserved_qty = frappe.db.sql("""
            SELECT SUM(qty) FROM `tabStock Reservation`
            WHERE item_code = %s
            AND serial_no IS NULL
            AND docstatus = 1
            AND status IN ('Reserved', 'In Use')
            AND (
                (from_date <= %s AND to_date >= %s)
                OR (from_date <= %s AND to_date >= %s)
                OR (from_date >= %s AND to_date <= %s)
            )
        """, (item_code, end_date, start_date, start_date, start_date, start_date, end_date))[0][0] or 0
        
        # Item is available if there's at least one unit available
        return (total_qty - reserved_qty) > 0
