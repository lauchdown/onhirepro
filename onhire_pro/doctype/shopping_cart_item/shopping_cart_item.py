from frappe.model.document import Document

class ShoppingCartItem(Document):
    def validate(self):
        self.update_amount()
        
    def update_amount(self):
        """Update amount based on quantity and rate"""
        self.amount = (self.qty or 0) * (self.rate or 0)
