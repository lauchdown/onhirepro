import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_url, now_datetime
import json
import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import base64

class XeroSettings(Document):
    def validate(self):
        if self.enabled:
            if not self.client_id or not self.client_secret or not self.redirect_uri:
                frappe.throw(_("Client ID, Client Secret and Redirect URI are required"))
    
    def get_authorization_url(self):
        """Get the authorization URL for Xero OAuth2"""
        if not self.client_id or not self.redirect_uri:
            frappe.throw(_("Client ID and Redirect URI are required"))
        
        oauth = OAuth2Session(
            self.client_id,
            redirect_uri=self.redirect_uri,
            scope=["offline_access", "accounting.transactions", "accounting.settings"]
        )
        
        authorization_url, state = oauth.authorization_url(
            "https://login.xero.com/identity/connect/authorize"
        )
        
        # Store state in cache for verification
        frappe.cache().set_value(
            f"xero_oauth_state_{frappe.session.user}",
            state,
            expires_in_sec=300
        )
        
        return authorization_url
    
    def handle_callback(self, authorization_response, state):
        """Handle the OAuth2 callback from Xero"""
        # Verify state
        cached_state = frappe.cache().get_value(f"xero_oauth_state_{frappe.session.user}")
        if not cached_state or cached_state != state:
            frappe.throw(_("Invalid OAuth state"))
        
        oauth = OAuth2Session(
            self.client_id,
            redirect_uri=self.redirect_uri,
            scope=["offline_access", "accounting.transactions", "accounting.settings"]
        )
        
        # Fetch token
        try:
            token = oauth.fetch_token(
                "https://identity.xero.com/connect/token",
                authorization_response=authorization_response,
                client_secret=self.client_secret
            )
        except Exception as e:
            frappe.log_error(str(e), "Xero Token Fetch Error")
            frappe.throw(_("Failed to fetch Xero token"))
        
        # Get tenant ID
        try:
            tenant_response = oauth.get(
                "https://api.xero.com/connections",
                headers={"Authorization": f"Bearer {token['access_token']}"}
            )
            tenant_response.raise_for_status()
            tenants = tenant_response.json()
            
            if not tenants:
                frappe.throw(_("No Xero organizations found"))
            
            # Use the first tenant
            tenant_id = tenants[0]["tenantId"]
        except Exception as e:
            frappe.log_error(str(e), "Xero Tenant Fetch Error")
            frappe.throw(_("Failed to fetch Xero tenant information"))
        
        # Update settings
        self.access_token = token["access_token"]
        self.refresh_token = token["refresh_token"]
        self.token_expiry = now_datetime().add(seconds=token["expires_in"])
        self.tenant_id = tenant_id
        self.authorization_status = "Authorized"
        self.save()
        
        return True
    
    def refresh_access_token(self):
        """Refresh the Xero access token"""
        if not self.refresh_token:
            frappe.throw(_("No refresh token available"))
        
        try:
            token_response = requests.post(
                "https://identity.xero.com/connect/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            token_response.raise_for_status()
            token = token_response.json()
            
            self.access_token = token["access_token"]
            self.refresh_token = token["refresh_token"]
            self.token_expiry = now_datetime().add(seconds=token["expires_in"])
            self.save()
            
            return True
        except Exception as e:
            frappe.log_error(str(e), "Xero Token Refresh Error")
            self.authorization_status = "Refresh Failed"
            self.save()
            return False
    
    def get_oauth_session(self):
        """Get an authenticated OAuth2 session for Xero API"""
        if not self.access_token or not self.refresh_token:
            return None
        
        token = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": "Bearer"
        }
        
        if self.token_expiry:
            token["expires_at"] = self.token_expiry.timestamp()
        
        def token_updater(token):
            self.access_token = token["access_token"]
            self.refresh_token = token["refresh_token"]
            self.token_expiry = now_datetime().add(seconds=token["expires_in"])
            self.save()
        
        session = OAuth2Session(
            self.client_id,
            token=token,
            auto_refresh_url="https://identity.xero.com/connect/token",
            auto_refresh_kwargs={
                "client_id": self.client_id,
                "client_secret": self.client_secret
            },
            token_updater=token_updater
        )
        
        return session
