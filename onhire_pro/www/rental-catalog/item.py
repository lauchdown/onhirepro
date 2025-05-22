import frappe
from frappe import _
from frappe.utils import getdate

def get_context(context):
    """Prepare context for rental item detail page"""
    
    # Get item code from URL
    item_code = frappe.form_dict.get('item_code') or context.get('item_code')
    
    if not item_code:
        # Extract item code from path
        path_parts = frappe.request.path.split('/')
        if len(path_parts) > 2:
            item_code = path_parts[-1]
    
    if not item_code:
        frappe.throw(_("Item not specified"), frappe.DoesNotExistError)
    
    # Get start and end dates from URL if provided
    start_date = frappe.form_dict.get('start_date')
    end_date = frappe.form_dict.get('end_date')
    
    # Set default dates if not provided
    if not start_date:
        start_date = frappe.utils.today()
    if not end_date:
        end_date = frappe.utils.add_days(start_date, 7)
    
    # Get item details
    item = frappe.get_doc("Item", item_code)
    
    # Check if item exists and is a rental item
    if not item or not item.get("is_rental_item"):
        frappe.throw(_("Invalid rental item"), frappe.DoesNotExistError)
    
    # Prepare item data for template
    context.item = {
        "name": item.name,
        "item_name": item.item_name,
        "item_group": item.item_group,
        "description": item.description,
        "image": item.image,
        "rate": item.get("standard_rate") or 0,
        "rental_period_unit": item.get("rental_period_unit") or "Day",
        "daily_rate": item.get("daily_rate") or item.get("standard_rate") or 0,
        "weekly_rate": item.get("weekly_rate") or (item.get("standard_rate") * 5 if item.get("standard_rate") else 0),
        "monthly_rate": item.get("monthly_rate") or (item.get("standard_rate") * 20 if item.get("standard_rate") else 0),
        "rental_terms": item.get("rental_terms"),
        "available": check_item_availability(item.name, start_date, end_date)
    }
    
    # Get additional images if any
    context.item["additional_images"] = []
    if item.get("website_image_list"):
        for img in item.website_image_list:
            if img.image:
                context.item["additional_images"].append(img.image)
    
    # Get specifications
    context.item["specifications"] = []
    if item.get("website_specifications"):
        for spec in item.website_specifications:
            context.item["specifications"].append({
                "label": spec.label,
                "value": spec.description
            })
    
    # Get similar items (same item group, also rental items)
    similar_items = frappe.get_all("Item", 
                                  filters={
                                      "item_group": item.item_group,
                                      "name": ["!=", item.name],
                                      "is_rental_item": 1,
                                      "disabled": 0,
                                      "show_in_website": 1
                                  },
                                  fields=["name", "item_name", "item_group", 
                                         "description", "image", "standard_rate as rate",
                                         "rental_period_unit", "daily_rate", "weekly_rate", "monthly_rate"],
                                  limit=4)
    
    context.similar_items = similar_items
    
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
