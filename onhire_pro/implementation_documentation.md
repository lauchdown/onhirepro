# OnHire Pro Quotation and Invoicing Implementation Documentation

## Overview

This document details the implementation of the Quotation and Invoicing module for the OnHire Pro app, including the design decisions, DocTypes created, and integration points with ERPNext's standard functionality.

## 1. Implemented DocTypes

### 1.1 Rental Job

The `Rental Job` DocType serves as the operational hub for managing rental processes. It connects sales orders to dispatch, return, and invoicing processes.

**Key Fields:**
- `sales_order`: Links to the originating Sales Order
- `customer`: Auto-fetched from Sales Order
- `job_status`: Tracks the rental job's lifecycle (Pending Preparation → Dispatched → Returned → Invoiced → Completed)
- `scheduled_dispatch_date` and `scheduled_return_date`: For planning
- `actual_dispatch_date` and `actual_return_date`: For tracking actual usage
- `items`: Child table of rental items

**Design Rationale:**
- Separating operational aspects from financial documents (Sales Order/Invoice) allows for more flexible rental management
- The status flow enables clear tracking of where items are in the rental lifecycle
- Date fields support both planning and actual usage tracking for accurate billing

### 1.2 Rental Job Item

This child table tracks individual items within a Rental Job, including their dispatch and return status.

**Key Fields:**
- `item_code` and `item_name`: Basic item identification
- `serial_no`: For serialized items
- `qty`: Quantity being rented
- `item_type`: Distinguishes between "Rental", "Sale", and "SOR - Sale or Return" items
- `dispatched_qty`, `returned_qty`, `damaged_qty`: For tracking item movement and condition
- `sor_converted_to_sale_qty`: Tracks SOR items that convert to sales due to damage or non-return

**Design Rationale:**
- Separate tracking of dispatched, returned, and damaged quantities enables partial returns and accurate invoicing
- The SOR conversion tracking supports the complex billing scenarios where rental items become sales

## 2. Enhanced Standard DocTypes

### 2.1 Quotation Enhancements

The standard ERPNext `Quotation` DocType was enhanced with rental-specific fields rather than creating a separate DocType, maintaining compatibility with standard ERPNext workflows.

**Header-Level Fields Added:**
- `is_rental_quotation`: Flag to identify rental quotes
- `rental_start_date` and `rental_end_date`: Define the overall rental period
- `calculated_total_rental_duration_display`: Shows duration in a human-readable format
- `rental_terms_and_conditions`: Rental-specific terms

**Item-Level Fields Added:**
- `item_type`: Distinguishes between "Rental", "Sale", and "SOR - Sale or Return" items
- `rental_item_start_date` and `rental_item_end_date`: Allow per-item rental periods
- `rental_item_duration`: Calculated field showing duration in billing units
- `rate_per_unit_duration`: The rate per time unit (hour/day/week)
- `rental_period_unit`: The time unit for billing

**Design Rationale:**
- Extending the standard Quotation maintains compatibility with ERPNext's sales workflow
- The flag approach (`is_rental_quotation`) allows the same DocType to serve both standard sales and rental scenarios
- Per-item rental dates provide flexibility for different items to have different rental periods within the same quote

### 2.2 Stock Entry Enhancements

The standard `Stock Entry` DocType was enhanced to support rental returns and condition assessment.

**Fields Added:**
- `rental_job`: Links returns to the originating Rental Job
- `condition_assessment`: Links returned items to their condition assessments

**Design Rationale:**
- Using standard Stock Entry for returns leverages ERPNext's inventory management
- The condition assessment linkage enables damage tracking and billing

## 3. Workflow and Business Logic

### 3.1 Quotation Approval Workflow

A custom workflow was implemented for rental quotations to ensure proper approval and reservation.

**States:**
- Draft → Pending Approval → Approved/Rejected → Ordered/Expired

**Key Transitions:**
- "Submit for Approval": Draft → Pending Approval (Sales/Rental User)
- "Approve": Pending Approval → Approved (Sales/Rental Manager)
- "Reject": Pending Approval → Rejected (Sales/Rental Manager)
- "Mark as Ordered": Approved → Ordered (Any role)

**Design Rationale:**
- The approval workflow ensures proper oversight for rental commitments
- The "Approved" state triggers stock reservations, ensuring inventory is held for confirmed quotes
- The "Ordered" state links to Sales Order creation and subsequent Rental Job creation

### 3.2 Stock Availability and Reservation

A comprehensive system was implemented to check item availability and create reservations.

**Key Components:**
- `validate_item_availability_for_quotation()`: Checks if items are available for the requested period
- `check_single_item_availability()`: Handles both serialized and non-serialized items
- `create_reservations_for_quotation()`: Creates reservations when quotes are approved

**Design Rationale:**
- Real-time availability checks prevent overbooking
- Separate handling for serialized and non-serialized items accommodates different inventory management approaches
- The reservation system ensures that approved quotes have guaranteed inventory

### 3.3 Damage Charge Handling

A system was implemented to assess damages and automatically add charges to invoices.

**Key Components:**
- `get_damage_charges_for_rental_job()`: Calculates charges based on condition assessments
- `add_damage_charges_to_invoice()`: Adds damage charges to Sales Invoices
- Integration with Damage Charge Rules for standardized billing

**Design Rationale:**
- Automated damage billing reduces manual work and ensures consistency
- The rule-based approach allows for standardized charging based on damage severity
- Integration with the invoice system ensures proper accounting

## 4. Integration Points

### 4.1 ERPNext Standard DocTypes

The implementation integrates with several standard ERPNext DocTypes:

- **Quotation**: Enhanced with rental fields
- **Sales Order**: Created from approved quotations
- **Stock Entry**: Used for returns with condition assessment links
- **Sales Invoice**: Enhanced to include damage charges

### 4.2 Custom Hooks

Several hooks were implemented to integrate the rental workflow:

- **Quotation Validation**: Checks item availability
- **Quotation Approval**: Creates stock reservations
- **Sales Invoice Creation**: Adds damage charges

## 5. Technical Implementation Notes

### 5.1 Custom Fields vs. Custom DocTypes

For most enhancements, we chose to extend standard DocTypes with custom fields rather than creating entirely new DocTypes. This approach:

- Maintains compatibility with standard ERPNext workflows
- Leverages existing UI and business logic
- Simplifies future upgrades

### 5.2 Fixtures

Custom fields and workflows are implemented as fixtures, allowing for:

- Version control of customizations
- Easy deployment across environments
- Consistent application setup

### 5.3 Server Scripts and Client Scripts

The implementation uses a combination of:

- Server-side validation for data integrity
- Client-side scripts for real-time feedback and calculations

## 6. Future Enhancements

The current implementation provides a solid foundation, but several enhancements could be considered:

- **Advanced Pricing Rules**: More sophisticated rental pricing based on duration tiers
- **Rental Package Discounts**: Special pricing for bundles of items
- **Seasonal Pricing**: Variable rates based on time of year
- **Integration with Maintenance Schedule**: To track maintenance needs based on rental usage

## 7. Conclusion

The Quotation and Invoicing module implementation provides a comprehensive solution for rental businesses, addressing the unique challenges of rental workflows while maintaining compatibility with ERPNext's standard functionality. The design choices prioritize flexibility, accuracy, and user experience, creating a system that can handle complex rental scenarios while remaining intuitive to use.
