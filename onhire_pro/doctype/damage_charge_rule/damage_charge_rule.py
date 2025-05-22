# Copyright (c) 2025, OnHire Pro and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DamageChargeRule(Document):
	def validate(self):
		if self.charge_type == "Percentage of Item Value" and not self.charge_percentage:
			frappe.throw("Charge Percentage is required when Charge Type is Percentage of Item Value")
		
		if self.charge_type == "Fixed Amount" and not self.fixed_charge_amount:
			frappe.throw("Fixed Charge Amount is required when Charge Type is Fixed Amount")
		
		# Validate charge percentage is between 0 and 100
		if self.charge_type == "Percentage of Item Value" and (self.charge_percentage <= 0 or self.charge_percentage > 100):
			frappe.throw("Charge Percentage must be between 0 and 100")
