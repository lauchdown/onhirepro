from frappe.model.document import Document

class ShoppingCart(Document):
    def validate(self):
        self.update_total_amount()
        
    def update_total_amount(self):
        """Update total amount based on items"""
        self.total_amount = sum((item.amount or 0) for item in self.items)
