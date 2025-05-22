import frappe
from frappe import _
from frappe.utils import flt, get_datetime

def get_damage_charges_for_rental_job(rental_job_name):
    """Retrieve damage charges for a given rental job based on condition assessments."""
    damage_charges = []
    condition_assessments = frappe.get_all(
        "Condition Assessment",
        filters={"reference_doctype": "Rental Job", "reference_name": rental_job_name, "docstatus": 1},
        fields=["name", "item_code", "serial_no", "assessed_condition", "damage_description", "estimated_repair_cost", "is_billable_damage"]
    )

    for ca in condition_assessments:
        if ca.is_billable_damage:
            # Apply Damage Charge Rule if exists
            charge_rule = frappe.get_all(
                "Damage Charge Rule",
                filters={"item_code": ca.item_code, "condition_level": ca.assessed_condition, "is_active": 1},
                fields=["charge_type", "fixed_charge_amount", "percentage_of_item_value", "charge_item_code"],
                limit=1
            )
            
            charge_amount = 0
            charge_description = f"Damage to {ca.item_code}" 
            if ca.serial_no: 
                charge_description += f" (SN: {ca.serial_no})"
            charge_description += f": {ca.damage_description or ca.assessed_condition}"
            
            charge_item_for_invoice = frappe.db.get_single_value("Rental Settings", "default_damage_charge_item") or "Damage Fee"

            if charge_rule:
                rule = charge_rule[0]
                charge_item_for_invoice = rule.charge_item_code or charge_item_for_invoice
                if rule.charge_type == "Fixed Amount":
                    charge_amount = rule.fixed_charge_amount
                elif rule.charge_type == "Percentage of Item Value":
                    item_value = frappe.db.get_value("Item Price", {"item_code": ca.item_code, "price_list": frappe.db.get_single_value("Buying Settings", "buying_price_list")}, "price_list_rate") or 
                                 frappe.db.get_value("Item", ca.item_code, "standard_rate") or 0
                    charge_amount = (flt(item_value) * flt(rule.percentage_of_item_value)) / 100
                # Add other charge types if necessary (e.g., Replacement Cost)
            elif ca.estimated_repair_cost and flt(ca.estimated_repair_cost) > 0:
                charge_amount = flt(ca.estimated_repair_cost)
            
            if charge_amount > 0:
                damage_charges.append({
                    "item_code": charge_item_for_invoice, # This should be a non-stock service item
                    "description": charge_description,
                    "qty": 1,
                    "rate": charge_amount,
                    "amount": charge_amount,
                    "cost_center": frappe.db.get_single_value("Company", frappe.defaults.get_user_default("Company")), # Default cost center
                    "income_account": frappe.db.get_value("Item", charge_item_for_invoice, "income_account") or frappe.db.get_value("Company", frappe.defaults.get_user_default("Company"), "default_income_account"),
                    "condition_assessment": ca.name
                })
    return damage_charges

def add_damage_charges_to_invoice(sales_invoice_doc, rental_job_name):
    """Add damage charges as line items to a sales invoice."""
    if not rental_job_name:
        return

    damage_charges = get_damage_charges_for_rental_job(rental_job_name)
    if not damage_charges:
        return

    for charge in damage_charges:
        # Check if this damage charge (from this CA) is already on the invoice
        already_added = False
        for item in sales_invoice_doc.items:
            if item.get("condition_assessment") == charge.get("condition_assessment") and item.item_code == charge.get("item_code"):
                already_added = True
                break
        if not already_added:
            sales_invoice_doc.append("items", charge)
    
    sales_invoice_doc.calculate_taxes_and_totals() # Recalculate totals

# This function would be called when creating/updating a Sales Invoice from a Rental Job
# For example, in a custom button or a server script on Sales Invoice

# Example hook for Sales Invoice (would go in hooks.py)
# doc_events = {
# "Sales Invoice": {
# "before_save": "onhire_pro.onhire_pro.invoice_utils.add_damage_charges_if_linked_to_rental_job"
# }
# }

def add_damage_charges_if_linked_to_rental_job(doc, method):
    # Assuming Sales Invoice has a custom field `rental_job` linking to Rental Job
    if doc.get("rental_job") and doc.is_new(): # Only add for new invoices or based on specific logic
        add_damage_charges_to_invoice(doc, doc.rental_job)
