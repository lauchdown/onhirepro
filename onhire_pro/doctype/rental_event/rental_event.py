# Copyright (c) 2025, OnHire Pro and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, add_to_date, cint, getdate, now_datetime, get_link_to_form

class RentalEvent(Document):
    def validate(self):
        self.validate_dates()
        self.validate_items()
        self.set_title_if_empty()
        self.detect_conflicts()
    
    def validate_dates(self):
        """Ensure end date is after start date"""
        start_date = get_datetime(self.start_date)
        end_date = get_datetime(self.end_date)
        
        if end_date <= start_date:
            frappe.throw("End Date must be after Start Date")
    
    def validate_items(self):
        """Ensure items are available for the event period"""
        if not self.items or len(self.items) == 0:
            return
        
        for item in self.items:
            # Validate item dates against event dates
            item_start = get_datetime(item.start_date)
            item_end = get_datetime(item.end_date)
            
            if item_start < get_datetime(self.start_date) or item_end > get_datetime(self.end_date):
                frappe.throw(f"Item {item.item_code} dates must be within event dates")
    
    def set_title_if_empty(self):
        """Set a default title if none is provided"""
        if not self.title:
            customer_name = frappe.get_value("Customer", self.customer, "customer_name") if self.customer else "No Customer"
            self.title = f"{self.event_type} - {customer_name} - {self.start_date}"
    
    def detect_conflicts(self):
        """Detect scheduling conflicts for serialized and non-serialized items"""
        if not self.items or len(self.items) == 0:
            return
            
        for item in self.items:
            if item.serial_no:
                # Check for serialized item conflicts
                self.detect_serialized_item_conflict(item)
            else:
                # Check for non-serialized item conflicts
                self.detect_non_serialized_item_conflict(item)
    
    def detect_serialized_item_conflict(self, item):
        """Check if a serialized item is already booked during the requested period"""
        conflicts = frappe.db.sql("""
            SELECT re.name, rei.serial_no, re.title, re.start_date, re.end_date
            FROM `tabRental Event Item` rei
            JOIN `tabRental Event` re ON rei.parent = re.name
            WHERE 
                rei.serial_no = %s
                AND re.name != %s
                AND re.docstatus = 1
                AND re.status IN ('Scheduled', 'Confirmed', 'In Progress')
                AND (
                    (rei.start_date <= %s AND rei.end_date >= %s)
                    OR (rei.start_date <= %s AND rei.end_date >= %s)
                    OR (rei.start_date >= %s AND rei.end_date <= %s)
                )
        """, (
            item.serial_no, 
            self.name or "New Rental Event",
            item.end_date, item.start_date,
            item.start_date, item.start_date,
            item.start_date, item.end_date
        ), as_dict=1)
        
        if conflicts:
            conflict = conflicts[0]
            frappe.throw(f"Serial No {item.serial_no} is already booked in Rental Event {conflict.name} ({conflict.title}) from {conflict.start_date} to {conflict.end_date}")
    
    def detect_non_serialized_item_conflict(self, item):
        """Check if enough quantity of a non-serialized item is available during the requested period"""
        # Get total quantity of this item booked during the period
        booked_qty = frappe.db.sql("""
            SELECT SUM(rei.qty) as total_qty
            FROM `tabRental Event Item` rei
            JOIN `tabRental Event` re ON rei.parent = re.name
            WHERE 
                rei.item_code = %s
                AND rei.serial_no IS NULL
                AND re.name != %s
                AND re.docstatus = 1
                AND re.status IN ('Scheduled', 'Confirmed', 'In Progress')
                AND (
                    (rei.start_date <= %s AND rei.end_date >= %s)
                    OR (rei.start_date <= %s AND rei.end_date >= %s)
                    OR (rei.start_date >= %s AND rei.end_date <= %s)
                )
        """, (
            item.item_code, 
            self.name or "New Rental Event",
            item.end_date, item.start_date,
            item.start_date, item.start_date,
            item.start_date, item.end_date
        ), as_dict=1)
        
        booked_qty = booked_qty[0].total_qty or 0
        
        # Get available quantity from stock
        available_qty = self.get_available_qty(item.item_code)
        
        if (booked_qty + item.qty) > available_qty:
            frappe.throw(f"Not enough quantity available for {item.item_code}. Requested: {item.qty}, Available: {available_qty - booked_qty}")
    
    def get_available_qty(self, item_code):
        """Get available quantity of an item from stock"""
        # This is a simplified version - in a real implementation, 
        # you would query the actual stock ledger or bin
        available_qty = frappe.db.sql("""
            SELECT SUM(actual_qty) as qty
            FROM `tabBin`
            WHERE item_code = %s
        """, (item_code), as_dict=1)
        
        return available_qty[0].qty or 0
    
    def on_submit(self):
        """Actions to take when event is submitted"""
        # Create reservations for items
        if self.items and self.status in ["Scheduled", "Confirmed"]:
            self.create_stock_reservations()
            
        # Schedule reminders
        if self.reminders:
            self.schedule_reminders()
    
    def create_stock_reservations(self):
        """Create stock reservations for items in the event"""
        for item in self.items:
            if item.serial_no:
                # Create serialized item reservation
                self.create_serialized_reservation(item)
            else:
                # Create non-serialized item reservation
                self.create_non_serialized_reservation(item)
    
    def create_serialized_reservation(self, item):
        """Create a reservation for a serialized item"""
        reservation = frappe.new_doc("Stock Reservation")
        reservation.item_code = item.item_code
        reservation.serial_no = item.serial_no
        reservation.qty = 1
        reservation.reservation_date = now_datetime()
        reservation.from_date = item.start_date
        reservation.to_date = item.end_date
        reservation.reference_doctype = "Rental Event"
        reservation.reference_name = self.name
        reservation.status = "Reserved"
        reservation.insert()
    
    def create_non_serialized_reservation(self, item):
        """Create a reservation for a non-serialized item"""
        reservation = frappe.new_doc("Stock Reservation")
        reservation.item_code = item.item_code
        reservation.qty = item.qty
        reservation.reservation_date = now_datetime()
        reservation.from_date = item.start_date
        reservation.to_date = item.end_date
        reservation.reference_doctype = "Rental Event"
        reservation.reference_name = self.name
        reservation.status = "Reserved"
        reservation.insert()
    
    def schedule_reminders(self):
        """Schedule reminders for the event"""
        for reminder in self.reminders:
            # Calculate reminder datetime based on lead time
            if reminder.time_unit == "Minutes":
                reminder_datetime = add_to_date(self.start_date, minutes=-cint(reminder.remind_before))
            elif reminder.time_unit == "Hours":
                reminder_datetime = add_to_date(self.start_date, hours=-cint(reminder.remind_before))
            elif reminder.time_unit == "Days":
                reminder_datetime = add_to_date(self.start_date, days=-cint(reminder.remind_before))
            
            # Create a background job for the reminder
            frappe.enqueue(
                "onhire_pro.onhire_pro.doctype.rental_event.rental_event.send_reminder",
                reminder=reminder.name,
                event=self.name,
                reminder_datetime=reminder_datetime,
                now=False,
                enqueue_after=reminder_datetime
            )
    
    def on_cancel(self):
        """Actions to take when event is cancelled"""
        # Cancel stock reservations
        reservations = frappe.get_all(
            "Stock Reservation",
            filters={
                "reference_doctype": "Rental Event",
                "reference_name": self.name,
                "docstatus": 1
            }
        )
        
        for reservation in reservations:
            res_doc = frappe.get_doc("Stock Reservation", reservation.name)
            res_doc.cancel()
        
        # Cancel scheduled reminders
        # This would require a mechanism to track and cancel background jobs

# Function to be called by background job for sending reminders
def send_reminder(reminder, event, reminder_datetime):
    """Send a reminder for a rental event"""
    reminder_doc = frappe.get_doc("Event Reminder", reminder)
    event_doc = frappe.get_doc("Rental Event", event)
    
    if reminder_doc.reminder_type == "Email" or reminder_doc.reminder_type == "Both":
        # Send email notification
        subject = f"Reminder: {event_doc.title}"
        message = f"""
        <p>This is a reminder for the following event:</p>
        <p><strong>{event_doc.title}</strong></p>
        <p>Start: {event_doc.start_date}</p>
        <p>End: {event_doc.end_date}</p>
        <p>Status: {event_doc.status}</p>
        <p>Click <a href="{get_link_to_form('Rental Event', event_doc.name)}">here</a> to view the event.</p>
        """
        
        frappe.sendmail(
            recipients=[reminder_doc.email_notification],
            subject=subject,
            message=message
        )
    
    if reminder_doc.reminder_type == "SMS" or reminder_doc.reminder_type == "Both":
        # Send SMS notification (if SMS gateway is configured)
        if reminder_doc.sms_notification:
            # This would require SMS gateway integration
            pass
    
    # Mark reminder as sent
    frappe.db.set_value("Event Reminder", reminder, "notification_sent", 1)
