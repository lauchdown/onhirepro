import frappe
from frappe.model.document import Document
from frappe.utils import getdate, cint

class Quotation(Document):
    def validate(self):
        self.validate_duplicate_rental_booking()
        self.map_rental_dates_to_standard_fields()

    def map_rental_dates_to_standard_fields(self):
        # If this Quotation is a rental request and uses custom date fields,
        # map them to standard or other custom fields on the Quotation for persistence.
        # This depends on how these dates are intended to be stored on the Quotation itself.
        # For example, custom_rental_start_date could map to valid_from (if appropriate)
        # or a new custom field on Quotation like 'rental_start_date_actual'.
        if cint(self.custom_is_rental_request) == 1:
            if self.custom_rental_start_date:
                # Example: self.valid_from = self.custom_rental_start_date
                # Or: self.rental_start_date_actual = self.custom_rental_start_date
                pass # Decide on actual field mapping
            if self.custom_rental_end_date:
                # Example: self.valid_till = self.custom_rental_end_date
                # Or: self.rental_end_date_actual = self.custom_rental_end_date
                pass # Decide on actual field mapping


    def validate_duplicate_rental_booking(self):
        # Only run this validation if it's a rental request
        # and has the necessary date fields populated.
        # The custom field 'custom_is_rental_request' should be added to Quotation DocType.
        if not cint(self.get("custom_is_rental_request")) == 1:
            return

        # Assuming custom_rental_start_date and custom_rental_end_date are fields on the Quotation
        # or have been mapped from the web form to actual fields on the Quotation DocType.
        # For this example, let's assume they are actual (possibly custom) fields on Quotation.
        
        start_date_field = "custom_rental_start_date" # Or the actual field name on Quotation
        end_date_field = "custom_rental_end_date"   # Or the actual field name on Quotation

        if not self.get(start_date_field) or not self.get(end_date_field) or not self.customer or not self.items:
            return # Not enough info for duplicate check

        current_start_date = getdate(self.get(start_date_field))
        current_end_date = getdate(self.get(end_date_field))
        
        current_item_codes = sorted([item.item_code for item in self.items])

        # Check for other non-cancelled, non-expired quotations
        # We look for quotations that are not 'Cancelled' and whose validity (if used for rental period) overlaps.
        # Or, more directly, compare against other 'custom_is_rental_request' quotations.
        
        potential_duplicates = frappe.get_all(
            "Quotation",
            filters={
                "customer": self.customer,
                "name": ["!=", self.name or "New Quotation-1"], # Exclude self if already saved
                "docstatus": ["!=", 2], # Not cancelled
                "status": ["not in", ["Lost", "Expired", "Cancelled", "Order Lost"]], # Active states
                "custom_is_rental_request": 1, # Ensure we are comparing rental requests
                # Date overlap condition:
                # (other_start < current_end) AND (other_end > current_start)
                start_date_field: ["<", current_end_date],
                end_date_field: [">", current_start_date],
            },
            fields=["name", start_date_field, end_date_field, "items.item_code"]
        )

        for dup in potential_duplicates:
            dup_items = frappe.get_all("Quotation Item", filters={"parent": dup.name}, fields=["item_code"])
            dup_item_codes = sorted([item.item_code for item in dup_items])

            if current_item_codes == dup_item_codes:
                # Check for exact date overlap (can be refined for partial overlaps if needed)
                dup_start_date = getdate(dup.get(start_date_field))
                dup_end_date = getdate(dup.get(end_date_field))

                # Basic overlap check (refined from DB query for clarity here)
                overlap = (max(current_start_date, dup_start_date) <= min(current_end_date, dup_end_date))
                
                if overlap:
                    link_to_dup = frappe.utils.get_link_to_form("Quotation", dup.name)
                    frappe.msgprint(
                        f"Warning: Potential duplicate booking detected. Quotation {link_to_dup} "
                        f"for customer {self.customer} has the same items and overlapping rental dates "
                        f"({dup_start_date} to {dup_end_date}).",
                        title="Potential Duplicate",
                        indicator="orange"
                    )
                    # Depending on policy, this could be frappe.throw to block submission
                    return # Stop after finding one potential duplicate for now
