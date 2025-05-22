import frappe
from frappe.model.document import Document
from frappe.utils import get_fullname, now_datetime

class Lead(Document):
    def validate(self):
        self.handle_portal_registration_status_change()

    def on_update(self):
        # on_update is also a good place if validate doesn't catch all status changes
        # or if some actions need to happen after save.
        # However, for this logic, validate should be sufficient if status is changed via UI/API.
        # self.handle_portal_registration_status_change() # Potentially redundant if validate handles it
        pass

    def handle_portal_registration_status_change(self):
        if self.is_new():
            return

        doc_before_save = self.get_doc_before_save()
        if not doc_before_save or doc_before_save.portal_registration_status == self.portal_registration_status:
            return # Status hasn't changed or it's a new doc

        if self.portal_registration_status == "Approved":
            self.approve_portal_registration()
        elif self.portal_registration_status == "Rejected":
            self.reject_portal_registration()

    def approve_portal_registration(self):
        frappe.log_info(f"Approving portal registration for Lead {self.name}", "LeadApproval")
        customer_name = None
        # 1. Check if Customer exists or create one
        if frappe.db.exists("Customer", {"customer_name": self.company_name}):
            customer_name = self.company_name
            frappe.msgprint(f"Customer '{customer_name}' already exists.")
        elif self.company_name:
            try:
                customer = frappe.new_doc("Customer")
                customer.customer_name = self.company_name
                customer.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups" # Default
                # Map other fields from Lead to Customer if necessary
                # customer.territory = ...
                # customer.customer_type = ...
                customer.insert(ignore_permissions=True)
                customer_name = customer.name
                frappe.msgprint(f"Customer '{customer_name}' created from Lead '{self.name}'.")
            except Exception as e:
                frappe.log_error(f"Failed to create Customer from Lead {self.name}: {e}", "LeadApproval")
                frappe.throw(f"Failed to create Customer: {e}")
                return
        else:
            frappe.throw("Company Name is required to create a Customer for portal registration.")
            return
        
        self.customer = customer_name # Link lead to customer
        self.status = "Converted" # Standard Lead status
        self.custom_converted_by = frappe.session.user
        self.custom_converted_on = now_datetime()

        # 2. Check if Contact exists or create one
        contact_name = None
        if frappe.db.exists("Contact", {"email_id": self.email_id}):
            contact_name = frappe.db.get_value("Contact", {"email_id": self.email_id}, "name")
            contact_doc = frappe.get_doc("Contact", contact_name)
            frappe.msgprint(f"Contact '{contact_name}' with email '{self.email_id}' already exists.")
        else:
            try:
                contact = frappe.new_doc("Contact")
                contact.first_name = self.first_name or self.lead_name.split(" ")[0]
                if self.last_name:
                    contact.last_name = self.last_name
                elif " " in self.lead_name:
                    contact.last_name = " ".join(self.lead_name.split(" ")[1:])
                
                contact.email_id = self.email_id
                contact.phone = self.phone or self.mobile_no
                # Link contact to customer
                contact.append("links", {
                    "link_doctype": "Customer",
                    "link_name": customer_name
                })
                contact.insert(ignore_permissions=True)
                contact_name = contact.name
                frappe.msgprint(f"Contact '{contact_name}' created for Lead '{self.name}'.")
            except Exception as e:
                frappe.log_error(f"Failed to create Contact from Lead {self.name}: {e}", "LeadApproval")
                frappe.throw(f"Failed to create Contact: {e}")
                return

        # 3. Flag Contact for portal access and create User
        if contact_name:
            contact_doc_for_portal = frappe.get_doc("Contact", contact_name)
            contact_doc_for_portal.is_portal_user = 1
            # Ensure user_id is cleared if we are about to create/link a new one based on this approval
            # This handles cases where a contact might exist but wasn't a portal user, or linked to a different user.
            contact_doc_for_portal.user_id = None 
            contact_doc_for_portal.save(ignore_permissions=True) 
            
            # Call the utility function to create/link the User record
            from onhire_pro.onhire_pro.customer_portal.utils import create_portal_user_for_contact
            create_portal_user_for_contact(contact_name)
        
        # 4. Send approval email
        self.send_portal_registration_email("approved")
        self.db_set("portal_registration_status", "Converted to Customer") # Final status after approval steps

    def reject_portal_registration(self):
        frappe.log_info(f"Rejecting portal registration for Lead {self.name}", "LeadRejection")
        # Send rejection email
        self.send_portal_registration_email("rejected")
        # Optionally, set Lead status to something like "Closed" or "Do Not Contact"
        # self.status = "Closed" 

    def send_portal_registration_email(self, mail_type):
        if not self.email_id:
            return

        subject = ""
        message = ""
        user_fullname = self.lead_name or self.first_name

        if mail_type == "approved":
            subject = "Your Portal Registration is Approved!"
            # TODO: Get portal URL from settings
            portal_url = frappe.utils.get_url("/login") # Default login, user will be redirected
            message = f"""Dear {user_fullname},

Your registration for our customer portal has been approved!
You can now log in using your email address ({self.email_id}) and the password you will set up (or was sent to you if a welcome email was triggered).

Access the portal here: {portal_url}

Thank you,
The Team"""
        elif mail_type == "rejected":
            subject = "Portal Registration Update"
            rejection_reason = self.custom_rejection_reason or "we are unable to approve your registration at this time." # Assuming a custom field for reason
            message = f"""Dear {user_fullname},

Thank you for your interest in our customer portal.
Unfortunately, {rejection_reason}

If you have any questions, please contact us.

Regards,
The Team"""

        if subject and message:
            try:
                frappe.sendmail(
                    recipients=[self.email_id],
                    subject=subject,
                    message=message,
                    now=True # Send immediately
                )
                frappe.msgprint(f"{mail_type.capitalize()} email sent to {self.email_id}.")
            except Exception as e:
                frappe.log_error(f"Failed to send portal registration {mail_type} email for Lead {self.name}: {e}", "LeadEmail")
