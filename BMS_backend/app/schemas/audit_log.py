from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_id: str          # UUID serialised as str for JSONB compat
    action: str
    table_name: Optional[str] = None
    record_id: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    ip_address: Optional[str] = None
    created_at: datetime

    # Resolved name (joined at query time)
    admin_name: Optional[str] = None
    admin_email: Optional[str] = None
