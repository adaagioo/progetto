"""
Audit logging utility for tracking sensitive operations.
"""
from datetime import datetime, timezone
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid


async def log_audit(
    db: AsyncIOMotorDatabase,
    restaurant_id: str,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """
    Log an audit entry.
    
    Args:
        db: MongoDB database instance
        restaurant_id: Restaurant ID
        user_id: User performing action
        action: Action type (create, update, delete, upload, etc.)
        entity_type: Type of entity (supplier, receiving, inventory, etc.)
        entity_id: ID of the entity affected
        details: Additional details about the action
        ip_address: IP address of the request
    """
    audit_entry = {
        "id": str(uuid.uuid4()),
        "restaurantId": restaurant_id,
        "userId": user_id,
        "action": action,
        "entityType": entity_type,
        "entityId": entity_id,
        "details": details or {},
        "ipAddress": ip_address,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.audit_logs.insert_one(audit_entry)


async def get_audit_logs(
    db: AsyncIOMotorDatabase,
    restaurant_id: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 100
) -> list:
    """
    Get audit logs for a restaurant.
    
    Args:
        db: MongoDB database instance
        restaurant_id: Restaurant ID
        entity_type: Filter by entity type
        entity_id: Filter by specific entity
        limit: Maximum number of logs to return
    
    Returns:
        List of audit log entries
    """
    query = {"restaurantId": restaurant_id}
    
    if entity_type:
        query["entityType"] = entity_type
    
    if entity_id:
        query["entityId"] = entity_id
    
    cursor = db.audit_logs.find(query).sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    
    # Remove MongoDB _id
    for log in logs:
        log.pop("_id", None)
    
    return logs
