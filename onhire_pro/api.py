import frappe
from frappe import _
import json
from frappe.utils import get_datetime, cint, flt, now
from frappe.utils.data import validate_json_string
from onhire_pro.utils.error_handler import handle_api_exception, log_error

def validate_input(data):
    """Validate input data with improved error handling"""
    try:
        if not isinstance(data, dict):
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    frappe.throw(_("Invalid JSON format"))
            else:
                frappe.throw(_("Invalid input: Expected dictionary or JSON string"))
        return data
    except Exception as e:
        log_error(e, "Input Validation")
        raise

@frappe.whitelist()
def get_or_create_shopping_cart():
    """Get current shopping cart with improved session handling"""
    try:
        if not frappe.session.user or frappe.session.user == 'Guest':
            frappe.throw(_("Please log in to manage your cart"))

        # Add rate limiting
        if frappe.cache().get_value(f"cart_creation_rate_limit:{frappe.session.user}"):
            frappe.throw(_("Please wait before creating another cart"))

        cart = frappe.get_all(
            "Shopping Cart",
            filters={
                "owner": frappe.session.user,
                "status": "Open",
                "creation": (">", now())  # Only get recent carts
            },
            limit=1
        )

        if cart:
            return frappe.get_doc("Shopping Cart", cart[0].name)
        else:
            # Set rate limit
            frappe.cache().set_value(
                f"cart_creation_rate_limit:{frappe.session.user}",
                1,
                expires_in_sec=5
            )
            
            new_cart = frappe.get_doc({
                "doctype": "Shopping Cart",
                "owner": frappe.session.user,
                "status": "Open",
                "expiry": now()  # Add cart expiry
            })
            new_cart.insert(ignore_permissions=True)
            return new_cart
    except Exception as e:
        return handle_api_exception(e)

@frappe.whitelist()
def add_to_cart(**kwargs):
    """Add item to cart with improved validation and error handling"""
    try:
        data = validate_input(kwargs)
        
        # Enhanced validation
        required_fields = ["item_code", "item_name", "qty", "rate"]
        for field in required_fields:
            if not data.get(field):
                frappe.throw(_(f"Missing required field: {field}"))
        
        # Validate item existence and availability
        if not frappe.db.exists("Item", data.get("item_code")):
            frappe.throw(_("Item does not exist"))
            
        # Get cart with error handling
        cart_doc = get_or_create_shopping_cart()
        if not cart_doc:
            frappe.throw(_("Unable to create or retrieve cart"))
        
        # Type conversion with validation
        try:
            qty = cint(data.get("qty"))
            rate = flt(data.get("rate"))
            is_sales_item = cint(data.get("is_sales_item", 0))
            is_rental_item = cint(data.get("is_rental_item", 0))
        except ValueError:
            frappe.throw(_("Invalid numeric values provided"))
        
        # Validate rental dates
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        if is_rental_item:
            if not start_date or not end_date:
                frappe.throw(_("Start date and end date are required for rental items"))
            try:
                start_date = get_datetime(start_date)
                end_date = get_datetime(end_date)
                if start_date >= end_date:
                    frappe.throw(_("End date must be after start date"))
            except Exception:
                frappe.throw(_("Invalid date format"))
        
        # Check stock availability
        if not is_rental_item and not check_stock_availability(data.get("item_code"), qty):
            frappe.throw(_("Insufficient stock available"))
        
        # Update or add item to cart
        item_found = False
        for item in cart_doc.items:
            if (item.item_code == data.get("item_code") and 
                item.is_rental_item == is_rental_item and 
                item.start_date == start_date and 
                item.end_date == end_date):
                
                item.qty += qty
                item.amount = item.qty * item.rate
                item_found = True
                break
        
        if not item_found:
            cart_doc.append("items", {
                "item_code": data.get("item_code"),
                "item_name": data.get("item_name"),
                "qty": qty,
                "rate": rate,
                "amount": qty * rate,
                "is_sales_item": is_sales_item,
                "is_rental_item": is_rental_item,
                "start_date": start_date,
                "end_date": end_date
            })
        
        cart_doc.save(ignore_permissions=True)
        
        # Return success response with cart details
        return {
            "success": True,
            "message": _("Item added to cart successfully"),
            "cart": cart_doc.as_dict()
        }
    except Exception as e:
        return handle_api_exception(e)

def check_stock_availability(item_code, qty):
    """Check if sufficient stock is available"""
    actual_qty = frappe.db.get_value("Bin", 
        {"item_code": item_code, "warehouse": get_default_warehouse()},
        "actual_qty") or 0
    return actual_qty >= qty

def get_default_warehouse():
    """Get default warehouse from settings"""
    return frappe.db.get_single_value("Stock Settings", "default_warehouse")

# Add the rest of the improved API functions...
