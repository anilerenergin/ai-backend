from pydantic import BaseModel
from typing import TypeVar, Generic, Optional, Any, List
from datetime import datetime

T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    data: Optional[Any] = None

# Your existing Job schemas
class JobOut(BaseModel):
    id: int
    prompt: str
    image_url: Optional[str] = None
    result_url: Optional[str] = None
    fal_request_id: Optional[str] = None
    application: Optional[str] = None
    status: str
    strength: Optional[float] = None
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Auth response schemas
class LoginResponseData(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email: str

class RegisterResponseData(BaseModel):
    user_id: int
    email: str

# Create specific response types
JobResponse = BaseResponse[JobOut]
JobListResponse = BaseResponse[List[JobOut]]
LoginResponse = BaseResponse[LoginResponseData]
RegisterResponse = BaseResponse[RegisterResponseData]