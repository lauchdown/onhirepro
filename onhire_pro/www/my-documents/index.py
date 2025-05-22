import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint, nowdate, get_datetime, time_diff_in_hours
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for documents page"""
    
    # Get rental portal settings
    settings = get_rental_portal_settings()
    
    # Check if portal is enabled
    if not settings.enable_rental_portal:
        frappe.throw(_("Customer Portal is not enabled"), frappe.PermissionError)
    
    # Add settings to context
    context.settings = settings
    
    # Add navigation items to context
    context.nav_items = get_portal_navigation_items()
    
    # Set breadcrumbs
    context.breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "My Documents", "url": "/my-documents"}
    ]
    
    # Get filter parameters from URL
    doc_type = frappe.form_dict.get('type', 'all')
    
    # Get customer linked to the current user
    customer = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    
    if not customer:
        context.documents = []
        context.error_message = "No customer account found for your user. Please contact support."
        return context
    
    # Get documents based on type
    context.documents = get_customer_documents(customer, doc_type)
    
    # Set active document type
    context.active_doc_type = doc_type
    
    # Get document type options
    context.doc_type_options = [
        {"value": "all", "label": "All Documents"},
        {"value": "contract", "label": "Contracts"},
        {"value": "invoice", "label": "Invoices"},
        {"value": "receipt", "label": "Receipts"},
        {"value": "condition", "label": "Condition Reports"},
        {"value": "other", "label": "Other Documents"}
    ]
    
    # Get pending signatures
    context.pending_signatures = get_pending_signatures(customer)
    
    return context

def get_customer_documents(customer, doc_type):
    """Get documents for the customer based on type"""
    
    # Initialize documents list
    documents = []
    
    # Get Sales Invoices
    if doc_type in ['all', 'invoice']:
        invoices = frappe.get_all("Sales Invoice", 
                                 filters={"customer": customer, "docstatus": 1},
                                 fields=["name", "posting_date", "grand_total", "status", "outstanding_amount"])
        
        for invoice in invoices:
            documents.append({
                "name": invoice.name,
                "title": f"Invoice {invoice.name}",
                "date": invoice.posting_date,
                "type": "invoice",
                "status": invoice.status,
                "amount": invoice.grand_total,
                "outstanding": invoice.outstanding_amount,
                "url": f"/printview?doctype=Sales Invoice&name={invoice.name}&format=Standard&no_letterhead=0&_lang=en",
                "can_download": True,
                "can_sign": False,
                "is_signed": True
            })
    
    # Get Payment Entries (Receipts)
    if doc_type in ['all', 'receipt']:
        receipts = frappe.get_all("Payment Entry", 
                                 filters={"party": customer, "docstatus": 1, "payment_type": "Receive"},
                                 fields=["name", "posting_date", "paid_amount", "reference_no"])
        
        for receipt in receipts:
            documents.append({
                "name": receipt.name,
                "title": f"Receipt {receipt.name}",
                "date": receipt.posting_date,
                "type": "receipt",
                "status": "Paid",
                "amount": receipt.paid_amount,
                "outstanding": 0,
                "url": f"/printview?doctype=Payment Entry&name={receipt.name}&format=Standard&no_letterhead=0&_lang=en",
                "can_download": True,
                "can_sign": False,
                "is_signed": True
            })
    
    # Get Rental Contracts
    if doc_type in ['all', 'contract']:
        contracts = frappe.get_all("Rental Booking Request", 
                                  filters={"customer": customer, "status": ["in", ["Approved", "In Progress"]]},
                                  fields=["name", "booking_reference", "booking_title", "booking_start_date", 
                                         "booking_end_date", "total_amount", "status"])
        
        for contract in contracts:
            # Check if contract document exists
            contract_doc_name = f"CONT-{contract.booking_reference}"
            contract_exists = frappe.db.exists("File", {"file_name": f"{contract_doc_name}.pdf"})
            
            # Check if contract is signed
            is_signed = frappe.db.exists("E-Signature Record", {"document_name": contract.name, "status": "Signed"})
            
            documents.append({
                "name": contract.name,
                "title": f"Rental Contract: {contract.booking_title}",
                "date": contract.booking_start_date,
                "type": "contract",
                "status": contract.status,
                "amount": contract.total_amount,
                "outstanding": 0,
                "url": f"/rental-contract?booking={contract.name}" if contract_exists else None,
                "can_download": contract_exists,
                "can_sign": not is_signed and contract.status == "Approved",
                "is_signed": is_signed,
                "end_date": contract.booking_end_date
            })
    
    # Get Condition Reports
    if doc_type in ['all', 'condition']:
        condition_reports = frappe.get_all("Condition Assessment", 
                                         filters={"customer": customer},
                                         fields=["name", "assessment_date", "item_code", "item_name", "status"])
        
        for report in condition_reports:
            documents.append({
                "name": report.name,
                "title": f"Condition Report: {report.item_name}",
                "date": report.assessment_date,
                "type": "condition",
                "status": report.status,
                "amount": 0,
                "outstanding": 0,
                "url": f"/printview?doctype=Condition Assessment&name={report.name}&format=Standard&no_letterhead=0&_lang=en",
                "can_download": True,
                "can_sign": False,
                "is_signed": True
            })
    
    # Sort documents by date (newest first)
    documents.sort(key=lambda x: x["date"], reverse=True)
    
    return documents

def get_pending_signatures(customer):
    """Get documents pending signature for the customer"""
    
    # Get contracts that need signature
    contracts = frappe.get_all("Rental Booking Request", 
                              filters={"customer": customer, "status": "Approved"},
                              fields=["name", "booking_reference", "booking_title"])
    
    pending_signatures = []
    
    for contract in contracts:
        # Check if contract is signed
        is_signed = frappe.db.exists("E-Signature Record", {"document_name": contract.name, "status": "Signed"})
        
        if not is_signed:
            pending_signatures.append({
                "name": contract.name,
                "title": f"Rental Contract: {contract.booking_title}",
                "reference": contract.booking_reference,
                "url": f"/sign-document?document={contract.name}&type=contract"
            })
    
    return pending_signatures
