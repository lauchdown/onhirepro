import frappe
import json
from frappe.utils import getdate, date_diff, flt, today, add_days, get_first_day, get_last_day, now_datetime
from frappe.utils.csvutils import build_csv_response


def create_portal_user_for_contact(contact_docname):
    """
    Creates or links a User record for a given Contact, enabling portal access.
    This function is intended to be called after a Contact is approved for portal access.
    """
    try:
        contact_doc = frappe.get_doc("Contact", contact_docname)
    except frappe.DoesNotExistError:
        frappe.log_error(f"Contact {contact_docname} not found.", "PortalUserCreation")
        return

    if not contact_doc.is_portal_user:
        frappe.log_info(f"Contact {contact_docname} is not flagged as a portal user. Skipping user creation.", "PortalUserCreation")
        return

    if contact_doc.user_id:
        frappe.log_info(f"Contact {contact_docname} already has a linked User ID: {contact_doc.user_id}. Ensuring roles.", "PortalUserCreation")
        try:
            user_doc = frappe.get_doc("User", contact_doc.user_id)
            roles_to_ensure = ["Website User", "Customer Portal User"]
            current_roles = [r.role for r in user_doc.get("roles")]
            made_change = False
            for role in roles_to_ensure:
                if role not in current_roles:
                    user_doc.add_roles(role)
                    made_change = True
            if made_change:
                 user_doc.save(ignore_permissions=True)
        except Exception as e_role:
            frappe.log_error(f"Failed to ensure roles for existing user {contact_doc.user_id} linked to contact {contact_docname}: {e_role}", "PortalUserCreation")
        return

    if not contact_doc.email_id:
        frappe.log_error(f"Contact {contact_docname} does not have an email ID. Cannot create portal user.", "PortalUserCreation")
        return

    if frappe.db.exists("User", contact_doc.email_id):
        existing_user_id = contact_doc.email_id
        frappe.log_info(f"User {existing_user_id} already exists with email from Contact {contact_docname}. Linking.", "PortalUserCreation")
        contact_doc.user_id = existing_user_id
        
        user_doc = frappe.get_doc("User", existing_user_id)
        user_doc.enabled = 1
        roles_to_add = ["Website User", "Customer Portal User"]
        current_roles = [r.role for r in user_doc.get("roles")]
        made_change_to_user = False
        for role in roles_to_add:
            if role not in current_roles:
                user_doc.add_roles(role)
                made_change_to_user = True
        
        if made_change_to_user or not user_doc.enabled:
            user_doc.save(ignore_permissions=True)

        contact_doc.save(ignore_permissions=True)
        frappe.msgprint(f"Contact {contact_doc.name} linked to existing User {existing_user_id}. Roles ensured.", indicator="green")
        return

    try:
        user = frappe.new_doc("User")
        user.email = contact_doc.email_id
        user.first_name = contact_doc.first_name
        if not user.first_name:
             user.first_name = contact_doc.email_id.split('@')[0] or "Portal User"
        user.last_name = contact_doc.last_name
        user.send_welcome_email = 1
        user.enabled = 1
        user.add_roles("Website User", "Customer Portal User")
        user.insert(ignore_permissions=True)
        frappe.msgprint(f"Portal User {user.name} created for Contact {contact_doc.name}.", indicator="green")

        contact_doc.user_id = user.name
        contact_doc.save(ignore_permissions=True)
        frappe.msgprint(f"Contact {contact_doc.name} linked to new User {user.name}.", indicator="green")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Failed to create portal user for Contact {contact_docname}")
        frappe.msgprint(f"Error creating portal user for {contact_docname}: {str(e)}", indicator="red", alert=True)


@frappe.whitelist()
def portal_search(search_term):
    if not search_term or len(search_term) < 3:
        return {"error": "Search term must be at least 3 characters long."}

    user = frappe.session.user
    if user == "Guest":
        return {"error": "Please log in to search."}

    results = {
        "rental_jobs": [],
        "documents": [], 
        "catalog_items": []
    }

    customer = frappe.db.get_value("User Permission", 
                                   {"user": user, "allow": "Customer", "apply_to_all_doctypes": 1}, 
                                   "for_value")
    if not customer:
        contact_name = frappe.db.get_value("Contact", {"user_id": user}, "name")
        if contact_name:
            customer = frappe.db.get_value("Dynamic Link", 
                                           {"parenttype": "Contact", "parent": contact_name, "link_doctype": "Customer"}, 
                                           "link_name")
    if customer:
        job_filters = [
            ["Rental Job", "customer", "=", customer],
            ["Rental Job", "docstatus", "=", 1],
            [
                ["Rental Job", "name", "like", f"%{search_term}%"],
                ["Rental Job", "project_name", "like", f"%{search_term}%"],
            ]
        ]
        jobs = frappe.get_list("Rental Job", 
                               filters=job_filters, 
                               fields=["name", "project_name", "status", "scheduled_dispatch_date"], 
                               limit=10,
                               or_filters=True)
        for job in jobs:
            job["link"] = frappe.utils.get_link_to_form("Rental Job", job.name)
            results["rental_jobs"].append(job)

        doc_types_to_search = {
            "Quotation": ["name", "status", "grand_total"],
            "Sales Invoice": ["name", "status", "grand_total", "due_date"]
        }
        for doctype, fields in doc_types_to_search.items():
            doc_filters = [
                [doctype, "customer", "=", customer],
                [doctype, "docstatus", "=", 1],
                [doctype, "name", "like", f"%{search_term}%"]
            ]
            docs = frappe.get_list(doctype, filters=doc_filters, fields=["name"] + fields, limit=5)
            for doc in docs:
                doc["doctype"] = doctype
                doc["link"] = frappe.utils.get_link_to_form(doctype, doc.name)
                results["documents"].append(doc)

    item_filters = [
        ["Item", "is_rental_item", "=", 1],
        ["Item", "disabled", "=", 0],
        [
            ["Item", "item_code", "like", f"%{search_term}%"],
            ["Item", "item_name", "like", f"%{search_term}%"],
            ["Item", "description", "like", f"%{search_term}%"]
        ]
    ]
    items = frappe.get_list("Item", 
                            filters=item_filters, 
                            fields=["item_code", "item_name", "item_group", "image"], 
                            limit=10,
                            or_filters=True)
    for item in items:
        item["link"] = frappe.utils.get_link_to_form("Item", item.item_code)
        results["catalog_items"].append(item)
        
    return results

@frappe.whitelist()
def check_multiple_item_availability(item_codes, start_date, end_date):
    try:
        item_codes_list = json.loads(item_codes)
    except json.JSONDecodeError:
        return {"error": "Invalid item_codes format. Expected a JSON string array."}

    if not start_date or not end_date:
        return {"error": "Start date and end date are required for availability check."}

    availability_map = {}
    for item_code in item_codes_list:
        availability_map[item_code] = {
            "available": True, 
            "reason": "Availability check placeholder - marked as available."
        }
    
    if len(item_codes_list) > 1:
        if item_codes_list[0] in availability_map: 
            availability_map[item_codes_list[0]] = {"available": False, "reason": "Booked (Demo)"}
        if item_codes_list[1] in availability_map:
             availability_map[item_codes_list[1]] = {"available": True, "reason": ""}
    return {"availability_map": availability_map}

@frappe.whitelist()
def get_rental_quote_estimate(items_data, start_date_str, end_date_str, customer=None):
    if not items_data or not start_date_str or not end_date_str:
        return {"error": "Missing required parameters (items, start date, or end date)."}

    try:
        items = json.loads(items_data)
        start_date = getdate(start_date_str)
        end_date = getdate(end_date_str)
    except json.JSONDecodeError:
        return {"error": "Invalid items_data format."}
    except Exception:
        return {"error": "Invalid date format."}

    if end_date < start_date:
        return {"error": "End date cannot be before start date."}

    rental_days = date_diff(end_date, start_date) + 1
    if rental_days <= 0: rental_days = 1

    try:
        rental_settings = frappe.get_single("Rental Settings")
        default_price_list = rental_settings.get("rental_price_list") or "Standard Selling"
    except Exception:
        default_price_list = "Standard Selling"

    grand_total = 0.0
    sub_total = 0.0
    total_surcharges = 0.0
    total_discounts = 0.0
    line_items_breakdown = []

    for item_detail in items:
        item_code = item_detail.get("item_code")
        qty = flt(item_detail.get("qty", 1))
        if qty <= 0: continue

        item_price_details = frappe.db.get_value("Item Price", {
            "item_code": item_code,
            "price_list": default_price_list
        }, ["price_list_rate", "uom"], as_dict=True)

        daily_rate = 0
        if item_price_details:
            daily_rate = flt(item_price_details.price_list_rate)
        else:
            daily_rate = flt(frappe.db.get_value("Item", item_code, "standard_rate"))
            if not daily_rate:
                 line_items_breakdown.append({
                    "item_code": item_code, "qty": qty, "rate": 0, "days": rental_days,
                    "line_total": 0, "error": "Rate not found"
                })
                 continue

        line_total_before_modifiers = daily_rate * qty * rental_days
        item_surcharge = 0.0 
        item_discount = 0.0
        line_total_after_modifiers = line_total_before_modifiers + item_surcharge - item_discount
        
        sub_total += line_total_after_modifiers
        total_surcharges += item_surcharge
        total_discounts += item_discount

        line_items_breakdown.append({
            "item_code": item_code,
            "item_name": frappe.db.get_value("Item", item_code, "item_name"),
            "qty": qty,
            "uom": item_price_details.get("uom") if item_price_details else frappe.db.get_value("Item", item_code, "stock_uom"),
            "rate_per_day": daily_rate,
            "rental_days": rental_days,
            "base_amount": line_total_before_modifiers,
            "surcharge": item_surcharge,
            "discount": item_discount,
            "line_total": line_total_after_modifiers
        })

    tax_amount = 0
    grand_total = sub_total + tax_amount

    return {
        "sub_total": round(sub_total, 2),
        "total_surcharges": round(total_surcharges, 2),
        "total_discounts": round(total_discounts, 2),
        "tax_amount": round(tax_amount, 2),
        "grand_total": round(grand_total, 2),
        "rental_days": rental_days,
        "line_items_breakdown": line_items_breakdown,
        "currency": frappe.get_doc("Company", frappe.defaults.get_user_default("company") or frappe.db.get_default("company")).default_currency
    }

@frappe.whitelist()
def get_current_user_customer_details():
    user = frappe.session.user
    if user == "Guest":
        return {}

    customer_name = None
    company = None

    customer_name = frappe.db.get_value("User Permission",
                                      {"user": user, "allow": "Customer", "apply_to_all_doctypes": 1},
                                      "for_value")
    if not customer_name:
        contact_name = frappe.db.get_value("Contact", {"user_id": user}, "name")
        if contact_name:
            customer_link_info = frappe.db.get_value("Dynamic Link",
                                                   {"parenttype": "Contact", "parent": contact_name, "link_doctype": "Customer"},
                                                   ["link_name", "parent"], as_dict=True)
            if customer_link_info:
                customer_name = customer_link_info.link_name
    
    if customer_name:
        company = frappe.defaults.get_user_default("company")
        if not company and frappe.db.has_column("Customer", "company"):
             customer_doc = frappe.get_doc("Customer", customer_name)
             company = customer_doc.get("company")
        if not company:
            all_companies = frappe.get_all("Company", fields=["name"])
            if len(all_companies) == 1:
                company = all_companies[0].name
        return {"customer_name": customer_name, "company": company}
    return {}


@frappe.whitelist()
def get_customer_documents(doc_type_filters=None, date_from=None, date_to=None):
    user = frappe.session.user
    if user == "Guest":
        return {"error": "Please log in to view documents."}

    customer = frappe.db.get_value("User Permission",
                                   {"user": user, "allow": "Customer", "apply_to_all_doctypes": 1},
                                   "for_value")
    if not customer:
        contact_name = frappe.db.get_value("Contact", {"user_id": user}, "name")
        if contact_name:
            customer = frappe.db.get_value("Dynamic Link",
                                           {"parenttype": "Contact", "parent": contact_name, "link_doctype": "Customer"},
                                           "link_name")
    if not customer:
        return {"error": "No customer linked to your user account."}

    all_documents = []
    doctypes_to_fetch = {
        "Quotation": ["name", "status", "grand_total", "currency", "transaction_date", "valid_till"],
        "Sales Invoice": ["name", "status", "grand_total", "currency", "posting_date", "due_date"],
        "Delivery Note": ["name", "status", "posting_date", "customer_name"] 
    }

    for doctype, fields in doctypes_to_fetch.items():
        filters = {"customer": customer, "docstatus": 1}
        docs = frappe.get_list(doctype, filters=filters, fields=fields + ["creation"], order_by="modified desc", limit=50)
        for doc in docs:
            doc["doctype"] = doctype
        all_documents.extend(docs)

    all_documents.sort(key=lambda x: getdate(x.get("transaction_date") or x.get("posting_date") or x.creation), reverse=True)
    return {"documents": all_documents[:100]}


@frappe.whitelist()
def export_customer_rental_history():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Please log in to export history.")
        return

    customer = frappe.db.get_value("User Permission",
                                   {"user": user, "allow": "Customer", "apply_to_all_doctypes": 1},
                                   "for_value")
    if not customer:
        contact_name = frappe.db.get_value("Contact", {"user_id": user}, "name")
        if contact_name:
            customer = frappe.db.get_value("Dynamic Link",
                                           {"parenttype": "Contact", "parent": contact_name, "link_doctype": "Customer"},
                                           "link_name")
    if not customer:
        frappe.throw("No customer linked to your user account.")
        return

    rental_jobs = frappe.get_all(
        "Rental Job",
        filters={"customer": customer, "docstatus": 1},
        fields=["name", "project_name", "status", "scheduled_dispatch_date", "scheduled_return_date", "grand_total", "currency"],
        order_by="scheduled_dispatch_date desc"
    )

    if not rental_jobs:
        return {"error": "No rental history found to export."}

    csv_data = []
    headers = ["Job ID", "Project Name", "Status", "Dispatch Date", "Return Date", "Total Amount", "Currency"]
    csv_data.append(headers)

    for job in rental_jobs:
        row = [
            job.get("name"),
            job.get("project_name", ""),
            job.get("status"),
            frappe.utils.formatdate(job.get("scheduled_dispatch_date")),
            frappe.utils.formatdate(job.get("scheduled_return_date")),
            job.get("grand_total", 0),
            job.get("currency", "")
        ]
        csv_data.append(row)
    
    output = ""
    for row_idx, row_val in enumerate(csv_data):
        output += ",".join([f'"{str(x).replace("\"", "\"\"")}"' for x in row_val]) + ("\n" if row_idx < len(csv_data) -1 else "")
    return {"csv_data": output}

@frappe.whitelist()
def get_customer_dashboard_data():
    user = frappe.session.user
    if user == "Guest":
        return {"error": "Please log in to view dashboard."}

    customer = frappe.db.get_value("User Permission",
                                   {"user": user, "allow": "Customer", "apply_to_all_doctypes": 1},
                                   "for_value")
    if not customer:
        contact_name = frappe.db.get_value("Contact", {"user_id": user}, "name")
        if contact_name:
            customer = frappe.db.get_value("Dynamic Link",
                                           {"parenttype": "Contact", "parent": contact_name, "link_doctype": "Customer"},
                                           "link_name")
    if not customer:
        return {"error": "No customer linked to your user account."}

    stats = {}
    now = today()
    ytd_start = get_first_day(now).replace(month=1, day=1)

    stats["active_rentals"] = frappe.db.count("Rental Job", {"customer": customer, "status": ["in", ["Dispatched", "In Use", "Ready for Dispatch", "Order Confirmed"]], "docstatus": 1})
    
    upcoming_return_date_limit = add_days(now, 7)
    stats["upcoming_returns"] = frappe.db.count("Rental Job", {
        "customer": customer, 
        "status": ["in", ["Dispatched", "In Use"]], 
        "scheduled_return_date": ["between", [now, upcoming_return_date_limit]],
        "docstatus": 1
    })

    total_spend_ytd_result = frappe.db.sql("""
        SELECT SUM(grand_total) as total_spend
        FROM `tabSales Invoice`
        WHERE customer = %(customer)s
        AND docstatus = 1
        AND posting_date >= %(ytd_start)s
    """, {"customer": customer, "ytd_start": ytd_start}, as_dict=1)
    stats["total_spend_ytd"] = flt(total_spend_ytd_result[0].total_spend if total_spend_ytd_result and total_spend_ytd_result[0] else 0)
    
    company_currency = frappe.get_doc("Company", frappe.defaults.get_user_default("company") or frappe.db.get_default("company")).default_currency
    stats["currency"] = company_currency

    completed_jobs = frappe.get_all("Rental Job", 
                                   filters={"customer": customer, "status": "Completed", "docstatus": 1}, 
                                   fields=["scheduled_dispatch_date", "scheduled_return_date"])
    total_duration_days = 0
    if completed_jobs:
        for job in completed_jobs:
            if job.scheduled_dispatch_date and job.scheduled_return_date:
                total_duration_days += date_diff(getdate(job.scheduled_return_date), getdate(job.scheduled_dispatch_date)) + 1
        stats["avg_rental_duration"] = round(total_duration_days / len(completed_jobs), 1) if len(completed_jobs) > 0 else 0
    else:
        stats["avg_rental_duration"] = 0

    stats["pending_sor_returns"] = frappe.db.count("Rental Job", {"customer": customer, "custom_sor_items_pending_return": 1, "docstatus": 1})
    stats["damage_charges_review"] = frappe.db.count("Sales Invoice", {"customer": customer, "custom_is_damage_charge_invoice": 1, "status": ["in", ["Draft", "To Be Submitted"]], "docstatus": 0})


    alerts = []
    notification_logs = frappe.get_all("Notification Log", 
        filters={"for_user": user, "read": 0, "type": "Alert"}, 
        fields=["subject", "document_type", "document_name", "email_content as message"],
        order_by="creation desc", 
        limit=5
    )
    for log in notification_logs:
        link = None
        if log.document_type and log.document_name:
            link = frappe.utils.get_link_to_form(log.document_type, log.document_name)
        alerts.append({
            "subject": log.subject or "Alert",
            "message": log.message or "You have a new alert.",
            "link": link,
            "type": "warning" 
        })

    charts_data = {}
    monthly_spend_labels = []
    monthly_spend_values = []
    for i in range(5, -1, -1): 
        month_start_obj = add_days(now, - (i * 30)) # Approximate
        month_start = get_first_day(month_start_obj)
        month_end = get_last_day(month_start_obj)
        
        spend = frappe.db.sql("""
            SELECT SUM(grand_total) 
            FROM `tabSales Invoice` 
            WHERE customer = %(customer)s AND docstatus = 1 AND 
            posting_date BETWEEN %(start)s AND %(end)s
        """, {"customer": customer, "start": month_start, "end": month_end})
        
        monthly_spend_labels.append(month_start.strftime("%b %Y"))
        monthly_spend_values.append(flt(spend[0][0] if spend and spend[0] else 0))
    
    charts_data["monthly_spend"] = {"labels": monthly_spend_labels, "values": monthly_spend_values}

    category_data = frappe.db.sql("""
        SELECT i.item_group, COUNT(DISTINCT rji.parent) as job_count
        FROM `tabRental Job Item` rji
        JOIN `tabItem` i ON rji.item_code = i.name
        JOIN `tabRental Job` rj ON rji.parent = rj.name
        WHERE rj.customer = %(customer)s AND rj.docstatus = 1
        GROUP BY i.item_group
        ORDER BY job_count DESC
        LIMIT 5
    """, {"customer": customer}, as_dict=1)

    charts_data["category_distribution"] = {
        "labels": [cd.item_group for cd in category_data],
        "values": [cd.job_count for cd in category_data]
    }

    return {
        "stats": stats,
        "alerts": alerts,
        "charts_data": charts_data
    }
