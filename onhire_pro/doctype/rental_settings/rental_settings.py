# Copyright (c) 2025, OnHire Pro and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime

class RentalSettings(Document):
    def get_xero_credentials(self):
        """
        Retrieves Xero API credentials securely.
        """
        return {
            "client_id": self.xero_client_id,
            "client_secret": self.get_password("xero_client_secret"),
            "redirect_uri": self.xero_redirect_uri,
            "access_token": self.get_password("xero_access_token"),
            "refresh_token": self.get_password("xero_refresh_token"),
            "token_expiry": self.xero_token_expiry,
            "tenant_id": self.get_password("xero_tenant_id")
        }

    def update_xero_tokens(self, access_token, refresh_token, expiry, tenant_id=None):
        """
        Updates Xero API tokens and tenant ID securely.
        """
        self.set_password("xero_access_token", access_token)
        self.set_password("xero_refresh_token", refresh_token)
        self.xero_token_expiry = expiry
        if tenant_id:
            self.set_password("xero_tenant_id", tenant_id)
        self.save(ignore_permissions=True)
        frappe.db.commit() # Commit changes immediately
