import frappe
from frappe.realtime import get_redis_connection
import json
from typing import Dict, Any

def emit_update(event: str, data: Dict[str, Any], user: str = None) -> None:
    """Emit real-time update to specific user or all users"""
    try:
        redis_conn = get_redis_connection()
        if not redis_conn:
            return

        message = {
            "event": event,
            "data": data,
            "timestamp": frappe.utils.now()
        }

        if user:
            redis_conn.publish(f"events:{user}", json.dumps(message))
        else:
            redis_conn.publish("events", json.dumps(message))
    except Exception as e:
        frappe.log_error(f"Real-time Update Error: {str(e)}")

def emit_cart_update(cart_doc, user: str = None) -> None:
    """Emit cart update event"""
    emit_update("cart_update", {
        "cart_id": cart_doc.name,
        "total_items": len(cart_doc.items),
        "total_amount": cart_doc.total_amount
    }, user)

def emit_order_status_update(order_doc) -> None:
    """Emit order status update event"""
    emit_update("order_status_update", {
        "order_id": order_doc.name,
        "status": order_doc.status,
        "updated_at": frappe.utils.now()
    }, order_doc.owner)

# Add more real-time update functions as needed...
