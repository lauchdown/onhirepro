# Custom Schema Requirements for OnHire Pro

## Overview
This document outlines the custom fields, doctypes, and dependencies required for the OnHire Pro application's reporting and dashboard functionality. These schema elements must exist in the ERPNext instance for the KPI calculations and dashboards to function correctly.

## Required DocTypes

### 1. Rental Job
**Description**: Core doctype for managing rental operations
**Fields**:
- `name`: Primary key (standard)
- `docstatus`: Document status (standard)
- `company`: Link to Company (standard)
- `customer`: Link to Customer (standard)
- `status`: Select field with options: 'Draft', 'Confirmed', 'Active', 'Completed', 'Closed', 'Cancelled'
- `rental_start_date`: Date field
- `rental_end_date`: Date field
- `actual_return_date`: Date field (nullable)
- `quotation`: Link to Quotation (nullable)
- `is_rental_job`: Check field (1 or 0)

### 2. Rental Job Item
**Description**: Child table for Rental Job items
**Parent**: Rental Job
**Fields**:
- `name`: Primary key (standard)
- `parent`: Link to parent Rental Job (standard)
- `parenttype`: Type of parent (standard)
- `parentfield`: Field in parent (standard)
- `item_code`: Link to Item
- `qty`: Float field for quantity
- `amount`: Currency field for line amount

### 3. Condition Assessment
**Description**: Doctype for tracking item condition before and after rental
**Fields**:
- `name`: Primary key (standard)
- `docstatus`: Document status (standard)
- `company`: Link to Company (standard)
- `rental_job`: Link to Rental Job
- `item_code`: Link to Item
- `assessment_date`: Date field
- `status`: Select field with options: 'Pending Pre-Rental', 'Completed Pre-Rental', 'Pending Post-Rental', 'Completed'
- `condition_rating`: Select field with options: 'Excellent', 'Good', 'Fair', 'Damaged', 'Severely Damaged', 'Beyond Repair'
- `repair_cost`: Currency field (nullable)

### 4. Maintenance Task
**Description**: Doctype for tracking maintenance activities on rental items
**Fields**:
- `name`: Primary key (standard)
- `docstatus`: Document status (standard)
- `company`: Link to Company (standard)
- `item_code`: Link to Item
- `start_date`: Date field
- `completion_date`: Date field (nullable)
- `status`: Select field with options: 'Pending', 'In Progress', 'Completed', 'Cancelled'
- `maintenance_type`: Select field with options: 'Preventive', 'Corrective', 'Post-Rental'

### 5. Item (Extended)
**Description**: Standard Item doctype with rental-specific fields
**Fields**:
- Standard Item fields
- `is_rental_item`: Check field (1 or 0)
- `rental_rate_daily`: Currency field
- `rental_rate_weekly`: Currency field
- `rental_rate_monthly`: Currency field

### 6. Quotation (Extended)
**Description**: Standard Quotation doctype with rental-specific fields
**Fields**:
- Standard Quotation fields
- `is_rental_quotation`: Check field (1 or 0)
- `rental_start_date`: Date field (nullable)
- `rental_end_date`: Date field (nullable)

### 7. Sales Invoice (Extended)
**Description**: Standard Sales Invoice doctype with rental-specific fields
**Fields**:
- Standard Sales Invoice fields
- `is_rental_invoice`: Check field (1 or 0)
- `rental_job`: Link to Rental Job (nullable)

## Field Dependencies

### KPI Calculation Dependencies

1. **Item Utilization Rate**:
   - Requires: `Rental Job`, `Rental Job Item`, `Item.is_rental_item`, `Bin.actual_qty`
   - SQL Joins: `Rental Job` → `Rental Job Item` → `Item` → `Bin`

2. **Average Rental Duration**:
   - Requires: `Rental Job.rental_start_date`, `Rental Job.rental_end_date`, `Rental Job.actual_return_date`
   - Calculations: Date difference between return and start dates

3. **Revenue per Item Category**:
   - Requires: `Rental Job`, `Rental Job Item.amount`, `Item.item_group`
   - SQL Joins: `Rental Job` → `Rental Job Item` → `Item`

4. **Maintenance Turnaround Time**:
   - Requires: `Maintenance Task.start_date`, `Maintenance Task.completion_date`
   - Calculations: Date difference between completion and start dates

5. **Booking Conversion Rate**:
   - Requires: `Quotation.is_rental_quotation`, `Rental Job.quotation`
   - SQL Joins: `Quotation` → `Rental Job`

6. **Customer Churn Rate**:
   - Requires: `Rental Job.customer`, `Rental Job.rental_start_date`
   - Calculations: Comparison of customer activity across time periods

7. **Damage Rate**:
   - Requires: `Rental Job`, `Condition Assessment.condition_rating`
   - SQL Joins: `Rental Job` → `Rental Job Item` → `Condition Assessment`

8. **Stock Reservation Conflicts**:
   - Requires: `Rental Job`, `Rental Job Item`, `Bin.actual_qty`
   - Calculations: Overlapping rental periods for same items

9. **Overdue Returns**:
   - Requires: `Rental Job.status`, `Rental Job.rental_end_date`, `Rental Job.actual_return_date`
   - Calculations: Comparison of current date with rental end date

10. **Active Rental Jobs**:
    - Requires: `Rental Job.status`, `Rental Job.rental_start_date`, `Rental Job.rental_end_date`
    - Calculations: Filtering by status and date range

11. **Total Rental Revenue**:
    - Requires: `Sales Invoice.is_rental_invoice`, `Sales Invoice.grand_total`
    - Calculations: Sum of invoice amounts for rental invoices

## Dashboard Schema Dependencies

1. **Operational Overview Dashboard**:
   - Requires: All KPIs related to active jobs, dispatches, returns, and conversion rates
   - Chart Types: Number cards, lists

2. **Inventory Health & Risk Dashboard**:
   - Requires: KPIs related to item utilization, maintenance, and stock conflicts
   - Chart Types: Number cards, lists, charts

3. **Financial Snapshot Dashboard**:
   - Requires: KPIs related to revenue, quotations, and invoices
   - Chart Types: Number cards, trend charts

## Schema Verification Strategy

1. **DocType Verification**:
   - Check existence of all required doctypes
   - Verify custom doctypes are installed

2. **Field Verification**:
   - For each doctype, verify all required fields exist
   - Check field types match expected types

3. **Fallback Strategy**:
   - For missing fields: Return safe default values
   - For missing doctypes: Log error and return empty dataset
   - For type mismatches: Attempt type conversion or return default

4. **Error Reporting**:
   - Log specific schema issues to help administrators fix configuration
   - Include doctype name, field name, and expected vs. actual type
