import frappe
from frappe import _
from frappe.utils import getdate, add_days, cint, nowdate, get_datetime, time_diff_in_hours, flt
from onhire_pro.doctype.rental_portal_settings.rental_portal_settings import get_rental_portal_settings, get_portal_navigation_items

def get_context(context):
    """Prepare context for sales catalog page"""
    
    # Get rental portal settings
    settings = get_rental_portal_settings()
    
    # Check if portal is enabled and sales catalog is enabled
    if not settings.enable_rental_portal:
        frappe.throw(_("Customer Portal is not enabled"), frappe.PermissionError)
    
    if not settings.enable_sales_catalog:
        frappe.throw(_("Sales Catalog is not enabled"), frappe.PermissionError)
    
    # Add settings to context
    context.settings = settings
    
    # Add navigation items to context
    context.nav_items = get_portal_navigation_items()
    
    # Set breadcrumbs
    context.breadcrumbs = [
        {"label": "Home", "url": "/"},
        {"label": "Sales Catalog", "url": "/sales-catalog"}
    ]
    
    # Get filter parameters from URL
    item_group = frappe.form_dict.get('item_group')
    search_query = frappe.form_dict.get('search')
    sort_by = frappe.form_dict.get('sort_by', settings.sales_default_sort_field)
    sort_order = frappe.form_dict.get('sort_order', settings.sales_default_sort_order)
    page = cint(frappe.form_dict.get('page', 1))
    
    # Get items per page from settings
    items_per_page = cint(settings.sales_items_per_page) or 12
    
    # Get sales items
    result = get_sales_items(
        item_group=item_group,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        items_per_page=items_per_page
    )
    
    # Add result to context
    context.update(result)
    
    # Add filter parameters to context
    context.item_group = item_group
    context.search_query = search_query
    context.sort_by = sort_by
    context.sort_order = sort_order
    context.current_page = page
    
    # Get item groups for filter
    context.item_groups = get_item_groups()
    
    # Get sort options
    context.sort_options = [
        {"value": "item_name", "label": "Item Name"},
        {"value": "price", "label": "Price"},
        {"value": "item_group", "label": "Category"}
    ]
    
    # Check if cart exists in session
    context.cart_count = get_cart_count()
    
    return context

def get_sales_items(item_group=None, search_query=None, sort_by="item_name", sort_order="asc", page=1, items_per_page=12):
    """Get sales items based on filters and pagination"""
    
    # Get settings
    settings = get_rental_portal_settings()
    
    # Start building filters
    filters = {"is_sales_item": 1, "disabled": 0}
    
    # Add item group filter if specified
    if item_group:
        filters["item_group"] = item_group
    
    # Get selected sales items from settings if enabled
    selected_items = []
    if settings.enable_sales_item_selection and settings.sales_item_selection:
        selected_items = [row.item_code for row in settings.sales_item_selection if row.enable_in_portal]
        
        if selected_items:
            filters["item_code"] = ["in", selected_items]
    
    # Build search condition
    search_condition = ""
    if search_query:
        search_condition = """
            AND (
                i.item_code LIKE %(search)s
                OR i.item_name LIKE %(search)s
                OR i.description LIKE %(search)s
            )
        """
    
    # Build order by clause
    order_by_map = {
        "item_name": "i.item_name",
        "item_group": "i.item_group",
        "price": "ip.price_list_rate"
    }
    
    order_by = order_by_map.get(sort_by, "i.item_name")
    order_direction = "ASC" if sort_order.lower() == "asc" else "DESC"
    
    # Calculate pagination
    start = (page - 1) * items_per_page
    
    # Get price list
    price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
    
    # Query to get items with stock information
    query = """
        SELECT 
            i.item_code,
            i.item_name,
            i.item_group,
            i.description,
            i.image,
            i.has_variants,
            ip.price_list_rate as price,
            COALESCE(SUM(b.actual_qty), 0) as stock_qty
        FROM 
            `tabItem` i
        LEFT JOIN 
            `tabItem Price` ip ON ip.item_code = i.item_code AND ip.price_list = %(price_list)s
        LEFT JOIN 
            `tabBin` b ON b.item_code = i.item_code
        WHERE 
            i.is_sales_item = 1
            AND i.disabled = 0
            {search_condition}
            {item_group_condition}
            {selected_items_condition}
        GROUP BY 
            i.item_code
        ORDER BY 
            {order_by} {order_direction}
        LIMIT %(start)s, %(items_per_page)s
    """
    
    # Add conditions based on filters
    item_group_condition = "AND i.item_group = %(item_group)s" if item_group else ""
    selected_items_condition = "AND i.item_code IN %(selected_items)s" if selected_items else ""
    
    # Format query with conditions
    query = query.format(
        search_condition=search_condition,
        item_group_condition=item_group_condition,
        selected_items_condition=selected_items_condition,
        order_by=order_by,
        order_direction=order_direction
    )
    
    # Execute query
    items = frappe.db.sql(query, {
        "price_list": price_list,
        "search": f"%{search_query}%" if search_query else "",
        "item_group": item_group,
        "selected_items": selected_items,
        "start": start,
        "items_per_page": items_per_page
    }, as_dict=True)
    
    # Count total items for pagination
    count_query = """
        SELECT 
            COUNT(DISTINCT i.item_code) as total
        FROM 
            `tabItem` i
        WHERE 
            i.is_sales_item = 1
            AND i.disabled = 0
            {search_condition}
            {item_group_condition}
            {selected_items_condition}
    """
    
    # Format count query with conditions
    count_query = count_query.format(
        search_condition=search_condition,
        item_group_condition=item_group_condition,
        selected_items_condition=selected_items_condition
    )
    
    # Execute count query
    total_items = frappe.db.sql(count_query, {
        "search": f"%{search_query}%" if search_query else "",
        "item_group": item_group,
        "selected_items": selected_items
    }, as_dict=True)[0].total
    
    # Calculate pagination info
    total_pages = (total_items + items_per_page - 1) // items_per_page
    has_next = page < total_pages
    has_prev = page > 1
    
    # Process items to add availability status
    for item in items:
        # Set availability status
        item.is_available = item.stock_qty > 0
        item.availability_status = "In Stock" if item.is_available else "Out of Stock"
        item.availability_class = "success" if item.is_available else "danger"
        
        # Format price
        item.formatted_price = frappe.format_value(item.price or 0, {"fieldtype": "Currency"})
        
        # Get item image URL
        if item.image:
            item.image_url = item.image
        else:
            item.image_url = "/assets/onhire_pro/images/no-image.png"
    
    return {
        "items": items,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev,
        "next_page": page + 1 if has_next else None,
        "prev_page": page - 1 if has_prev else None,
        "showing_start": start + 1 if items else 0,
        "showing_end": min(start + items_per_page, total_items)
    }

def get_item_groups():
    """Get item groups for filter"""
    
    # Get settings
    settings = get_rental_portal_settings()
    
    # Get selected sales items from settings if enabled
    selected_items = []
    if settings.enable_sales_item_selection and settings.sales_item_selection:
        selected_items = [row.item_code for row in settings.sales_item_selection if row.enable_in_portal]
    
    # Build query to get item groups
    query = """
        SELECT DISTINCT 
            i.item_group
        FROM 
            `tabItem` i
        WHERE 
            i.is_sales_item = 1
            AND i.disabled = 0
            {selected_items_condition}
        ORDER BY 
            i.item_group
    """
    
    # Add condition for selected items
    selected_items_condition = "AND i.item_code IN %(selected_items)s" if selected_items else ""
    
    # Format query with conditions
    query = query.format(
        selected_items_condition=selected_items_condition
    )
    
    # Execute query
    item_groups = frappe.db.sql(query, {
        "selected_items": selected_items
    }, as_dict=True)
    
    return [group.item_group for group in item_groups]

def get_cart_count():
    """Get number of items in cart"""
    
    # Get cart from session
    cart = frappe.cache().get_value(f"cart_{frappe.session.user}")
    
    if not cart:
        return 0
    
    # Count items in cart
    return sum(item.get("qty", 0) for item in cart.get("items", []))
