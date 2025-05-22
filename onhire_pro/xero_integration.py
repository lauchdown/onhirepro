import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime
import json
import requests
from requests_oauthlib import OAuth2Session
from tenacity import retry, stop_after_attempt, wait_exponential
from .utils.error_handler import log_error, OnHireProError, handle_api_exception

class XeroSyncError(OnHireProError):
    """Exception raised for Xero sync errors."""
    pass

class XeroAuthError(OnHireProError):
    """Exception raised for Xero authentication errors."""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry_error_callback=lambda retry_state: handle_sync_failure(retry_state)
)
def sync_invoice_to_xero(invoice_name):
    """
    Sync a Sales Invoice to Xero with retry mechanism
    
    Args:
        invoice_name (str): Sales Invoice name
    
    Returns:
        dict: Response from Xero API
    """
    try:
        # Get the invoice
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
        
        # Update sync status
        invoice.db_set('xero_sync_status', 'In Progress')
        
        # Get Xero session
        settings = get_xero_settings()
        session = settings.get_oauth_session()
        if not session:
            raise XeroAuthError("Xero integration is not authorized")
        
        # Prepare invoice data for Xero
        xero_invoice = prepare_xero_invoice(invoice)
        
        # Send to Xero
        response = session.post(
            "https://api.xero.com/api.xro/2.0/Invoices",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Xero-Tenant-Id": settings.tenant_id
            },
            json={"Invoices": [xero_invoice]}
        )
        response.raise_for_status()
        result = response.json()
        
        # Update invoice with Xero ID
        if result.get("Invoices") and len(result["Invoices"]) > 0:
            xero_id = result["Invoices"][0].get("InvoiceID")
            if xero_id:
                invoice.db_set("xero_invoice_id", xero_id)
                invoice.db_set("xero_sync_status", "Synced")
                invoice.add_comment("Comment", f"Synced to Xero with ID: {xero_id}")
                
                # Update last sync timestamp
                settings.last_sync_timestamp = now_datetime()
                settings.save()
        
        return result
    
    except requests.exceptions.RequestException as e:
        error_msg = parse_xero_error(e)
        log_error(
            e,
            "Xero Sync",
            {
                "invoice": invoice_name,
                "error_details": error_msg,
                "response": e.response.text if hasattr(e, 'response') else 'No response'
            }
        )
        raise XeroSyncError(f"Failed to sync invoice: {error_msg}")
    
    except Exception as e:
        log_error(
            e,
            "Xero Sync",
            {"invoice": invoice_name}
        )
        raise XeroSyncError(f"Unexpected error during sync: {str(e)}")

def handle_sync_failure(retry_state):
    """Handle final failure after all retries are exhausted"""
    exception = retry_state.outcome.exception()
    invoice_name = retry_state.args[0]
    
    try:
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
        invoice.db_set("xero_sync_status", "Failed")
        invoice.add_comment(
            "Comment",
            f"Failed to sync to Xero after {retry_state.attempt_number} attempts: {str(exception)}"
        )
    except Exception as e:
        log_error(e, "Sync Failure Handling", {"invoice": invoice_name})
    
    return None

def prepare_xero_invoice(invoice):
    """Prepare invoice data for Xero API"""
    settings = get_xero_settings()
    
    xero_invoice = {
        "Type": "ACCREC",
        "Contact": {
            "Name": invoice.customer_name
        },
        "Date": invoice.posting_date.strftime("%Y-%m-%d"),
        "DueDate": invoice.due_date.strftime("%Y-%m-%d"),
        "InvoiceNumber": invoice.name,
        "Reference": f"ERPNext Invoice {invoice.name}",
        "Status": "AUTHORISED",
        "LineItems": [],
        "CurrencyCode": invoice.currency
    }
    
    # Add line items
    for item in invoice.items:
        xero_line = {
            "Description": item.description or item.item_name,
            "Quantity": item.qty,
            "UnitAmount": item.rate,
            "AccountCode": settings.default_account_code,
            "TaxType": settings.default_tax_type,
            "LineAmount": item.amount
        }
        xero_invoice["LineItems"].append(xero_line)
    
    # Add taxes if applicable
    if invoice.taxes:
        for tax in invoice.taxes:
            tax_line = {
                "Description": tax.description,
                "Quantity": 1,
                "UnitAmount": tax.tax_amount,
                "AccountCode": settings.default_account_code,
                "TaxType": settings.default_tax_type,
                "LineAmount": tax.tax_amount
            }
            xero_invoice["LineItems"].append(tax_line)
    
    return xero_invoice

def parse_xero_error(error):
    """Parse Xero API error response"""
    if not hasattr(error, 'response') or not error.response:
        return str(error)
    
    try:
        error_data = error.response.json()
        if 'Elements' in error_data:
            return error_data['Elements'][0].get('ValidationErrors', [{}])[0].get('Message', str(error))
        return error_data.get('Message', str(error))
    except:
        return str(error)

def schedule_invoice_sync():
    """Schedule sync of pending invoices to Xero"""
    settings = get_xero_settings()
    if not settings.auto_sync_invoices:
        return
    
    # Get invoices that haven't been synced
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "xero_invoice_id": ("is", "not set"),
            "xero_sync_status": ["in", ["Not Synced", "Failed"]],
            "modified": (">", settings.last_sync_timestamp or "2000-01-01")
        },
        fields=["name"]
    )
    
    for invoice in invoices:
        try:
            sync_invoice_to_xero(invoice.name)
        except Exception as e:
            log_error(
                e,
                "Xero Auto Sync",
                {"invoice": invoice.name}
            )

def retry_failed_syncs():
    """Retry failed Xero syncs"""
    failed_invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "xero_sync_status": "Failed"
        },
        fields=["name"]
    )
    
    for invoice in failed_invoices:
        try:
            sync_invoice_to_xero(invoice.name)
        except Exception as e:
            log_error(
                e,
                "Xero Sync Retry",
                {"invoice": invoice.name}
            )
