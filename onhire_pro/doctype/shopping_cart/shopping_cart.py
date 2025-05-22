import frappe
from frappe.model.document import Document
from frappe.utils import now, add_days, get_datetime
from typing import List, Dict

class ShoppingCart(Document):
    def validate(self):
        self.validate_items()
        self.set_expiry()
        self.calculate_totals()
    
    def validate_items(self):
        """Validate cart items"""
        for item in self.items:
            if not frappe.db.exists("Item", item.item_code):
                frappe.throw(f"Item {item.item_code} does not exist")
            
            if item.qty <= 0:
                frappe.throw(f"Quantity must be greater than 0 for {item.item_code}")
    
    def set_expiry(self):
        """Set cart expiry time"""
        if not self.expiry:
            self.expiry = add_days(now(), 1)
    
    def calculate_totals(self):
        """Calculate cart totals"""
        self.total_amount = sum(item.amount for item in self.items)
        self.total_items = len(self.items)
    
    def is_expired(self) -> bool:
        """Check if cart is expired"""
        return get_datetime(self.expiry) < get_datetime(now())
    
    def cleanup_expired_items(self):
        """Remove expired items from cart"""
        self.items = [item for item in self.items if not self._is_item_expired(item)]
        self.save()
    
    def _is_item_expired(self, item) -> bool:
        """Check if cart item is expired"""
        if item.is_rental_item:
            return get_datetime(item.end_date) < get_datetime(now())
        return False
    
    def get_available_items(self) -> List[Dict]:
        """Get items that are still available"""
        available_items = []
        for item in self.items:
            if item.is_rental_item:
                if self._check_rental_availability(item):
                    available_items.append(item)
            else:
                if self._check_stock_availability(item):
                    available_items.append(item)
        return available_items
    
    def _check_rental_availability(self, item) -> bool:
        """Check rental item availability"""
        # Implementation for checking rental availability
        pass
    
    def _check_stock_availability(self, item) -> bool:
        """Check stock item availability"""
        actual_qty = frappe.db.get_value("Bin",
            {"item_code": item.item_code, "warehouse": self.get_default_warehouse()},
            "actual_qty") or 0
        return actual_qty >= item.qty
    
    @staticmethod
    def get_default_warehouse():
        """Get default warehouse from settings"""
        return frappe.db.get_single_value("Stock Settings", "default_warehouse")

def cleanup_expired_carts():
    """Cleanup expired shopping carts"""
    expired_carts = frappe.get_all(
        "Shopping Cart",
        filters={
            "status": "Open",
            "expiry": ("<", now())
        }
    )
    
    for cart in expired_carts:
        doc = frappe.get_doc("Shopping Cart", cart.name)
        doc.status = "Expired"
        doc.save()

# Add more shopping cart related functions...
