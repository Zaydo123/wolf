from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class User(BaseModel):
    id: str
    email: str
    name: Optional[str] = "Zayd"  # Default to Zayd when no name is provided
    phone_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True 