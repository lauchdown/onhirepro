# Copyright (c) 2025, OnHire Pro and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, now_datetime, cint, flt

class RentalBookingRequest(Document):
    def validate(self):
        self.validate_dates()
        self.validate_items()
        self.calculate_totals()
        self.set_booking_reference()
        
    def before_save(self):
        # Set status change timestamps and users
        if self.has_value_changed('status'):
            if self.status == 'Approved':
                self.approved_by = frappe.session.user
                self.approved_date = now_datetime()
            elif self.status == 'Rejected':
                self.rejected_by = frappe.session.user
                self.rejected_date = now_datetime()
    
    def on_update(self):
        # Send notifications on status change
        if self.has_value_changed('status'):
            self.send_status_notification()
    
    def validate_dates(self):
        """Validate booking start and end dates"""
        if getdate(self.booking_start_date) > getdate(self.booking_end_date):
            frappe.throw(_("End Date cannot be before Start Date"))
        
        if getdate(self.booking_start_date) < getdate(nowdate()):
            frappe.throw(_("Start Date cannot be in the past"))
    
    def validate_items(self):
        """Validate booking items"""
        if not self.items:
            frappe.throw(_("At least one item is required for booking"))
        
        # Check if there are any rental items
        has_rental_items = False
        for item in self.items:
            if item.is_rental_item:
                has_rental_items = True
                break
        
        # If delivery method is selected, ensure there's a delivery address
        if self.delivery_method == "delivery" and not self.delivery_address:
            frappe.throw(_("Delivery Address is required for delivery method"))
    
    def calculate_totals(self):
        """Calculate booking totals"""
        self.total_amount = sum(item.amount for item in self.items)
        self.total_tax = flt(self.total_amount * 0.1)  # 10% tax rate
        self.grand_total = flt(self.total_amount + self.total_tax)
    
    def set_booking_reference(self):
        """Set booking reference if not already set"""
        if not self.booking_reference:
            self.booking_reference = self.name
    
    def send_status_notification(self):
        """Send notification to customer on status change"""
        subject = ""
        message = ""
        
        if self.status == "Approved":
            subject = _("Your Booking Request {0} has been Approved").format(self.booking_reference)
            message = _("""
                <p>Dear {0},</p>
                <p>We're pleased to inform you that your booking request <strong>{1}</strong> has been approved.</p>
                <p><strong>Booking Details:</strong></p>
                <ul>
                    <li>Booking Reference: {1}</li>
                    <li>Start Date: {2}</li>
                    <li>End Date: {3}</li>
                    <li>Total Amount: {4}</li>
                </ul>
                <p>You can view the full details of your booking in your customer portal.</p>
                <p>Thank you for choosing our services!</p>
            """).format(
                self.customer_name,
                self.booking_reference,
                self.booking_start_date,
                self.booking_end_date,
                frappe.utils.fmt_money(self.grand_total)
            )
        
        elif self.status == "Rejected":
            subject = _("Your Booking Request {0} has been Rejected").format(self.booking_reference)
            message = _("""
                <p>Dear {0},</p>
                <p>We regret to inform you that your booking request <strong>{1}</strong> has been rejected.</p>
                <p><strong>Reason for Rejection:</strong> {2}</p>
                <p>If you have any questions or would like to discuss alternative options, please contact our customer service team.</p>
                <p>Thank you for your understanding.</p>
            """).format(
                self.customer_name,
                self.booking_reference,
                self.rejection_reason or "Not specified"
            )
        
        elif self.status == "In Progress":
            subject = _("Your Booking {0} is Now In Progress").format(self.booking_reference)
            message = _("""
                <p>Dear {0},</p>
                <p>Your booking <strong>{1}</strong> is now in progress.</p>
                <p>You can view the full details of your booking in your customer portal.</p>
                <p>Thank you for choosing our services!</p>
            """).format(
                self.customer_name,
                self.booking_reference
            )
        
        elif self.status == "Completed":
            subject = _("Your Booking {0} has been Completed").format(self.booking_reference)
            message = _("""
                <p>Dear {0},</p>
                <p>Your booking <strong>{1}</strong> has been marked as completed.</p>
                <p>We hope you were satisfied with our service. If you have any feedback, please let us know.</p>
                <p>Thank you for choosing our services!</p>
            """).format(
                self.customer_name,
                self.booking_reference
            )
        
        # Send email notification if subject and message are set
        if subject and message:
            # Get customer email
            customer_email = frappe.db.get_value("Customer", self.customer, "email_id")
            if customer_email:
                frappe.sendmail(
                    recipients=customer_email,
                    subject=subject,
                    message=message
                )
