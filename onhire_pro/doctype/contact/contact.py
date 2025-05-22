import frappe
from frappe.model.document import Document
from frappe.permissions import add_user_permission, remove_user_permission

class Contact(Document):
    def on_update(self):
        self.manage_customer_user_permission()
        self.handle_critical_field_changes_for_portal()

    def manage_customer_user_permission(self):
        if self.is_portal_user and self.user_id:
            customer_link = frappe.db.get_value("Dynamic Link", {
                "parenttype": "Contact",
                "parent": self.name,
                "link_doctype": "Customer"
            }, "link_name")

            if customer_link:
                try:
                    existing_permission = frappe.db.exists("User Permission", {
                        "user": self.user_id,
                        "allow": "Customer",
                        "for_value": customer_link,
                        "apply_to_all_doctypes": 1
                    })
                    if not existing_permission:
                        add_user_permission("Customer", customer_link, self.user_id, apply_to_all_doctypes=1)
                        frappe.msgprint(f"User Permission added for User '{self.user_id}' to access Customer '{customer_link}'.")
                    else:
                        frappe.log_info(f"User Permission already exists for User '{self.user_id}' and Customer '{customer_link}'.", "ContactUserPermission")
                except Exception as e:
                    frappe.log_error(f"Failed to add User Permission for Contact {self.name}, User {self.user_id}, Customer {customer_link}: {e}", "ContactUserPermission")
            else:
                frappe.log_info(f"Contact {self.name} is a portal user but not linked to any Customer. Skipping User Permission creation.", "ContactUserPermission")

    def handle_critical_field_changes_for_portal(self):
        if frappe.session.user == self.user_id and not self.is_new(): # Check if change is made by the portal user themselves
            doc_before_save = self.get_doc_before_save()
            if not doc_before_save:
                return

            # Define critical fields that need approval if changed by portal user
            # Email is typically not allowed to be changed by user directly in portal form for security.
            # Address changes might be critical.
            critical_fields_to_monitor = {
                "phone": "Primary Phone",
                "mobile_no": "Mobile Number",
                # Add other fields like 'address_line1', 'city' if they are directly on Contact and considered critical.
                # If address is a separate linked document, its changes need separate handling.
            }
            
            changed_critical_fields = []
            for field, label in critical_fields_to_monitor.items():
                if self.get(field) != doc_before_save.get(field):
                    changed_critical_fields.append(f"{label} (from '{doc_before_save.get(field)}' to '{self.get(field)}')")
            
            if changed_critical_fields:
                # Option 1: Revert and create approval (more complex)
                # Option 2: Allow change but notify admin (simpler for now)
                
                admin_subject = f"Portal User Profile Update Requires Review: Contact {self.name}"
                admin_message = f"""User {self.user_id} (Contact: {self.name}) has updated the following critical profile information via the portal:
                
                {', '.join(changed_critical_fields)}

                Please review these changes.
                Contact Link: {frappe.utils.get_link_to_form('Contact', self.name)}
                User Link: {frappe.utils.get_link_to_form('User', self.user_id)}
                """
                
                # Notify System Managers (or a specific role for portal admin)
                system_managers = frappe.get_users_with_role("System Manager")
                if system_managers:
                    frappe.sendmail(
                        recipients=system_managers,
                        subject=admin_subject,
                        message=admin_message,
                        now=True 
                    )
                frappe.msgprint("Your profile changes have been saved. Some critical changes will be reviewed by an administrator.", indicator="blue", alert=True)
