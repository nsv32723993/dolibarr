from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class TenantConfigBase(BaseModel):
    tenant_id: Optional[int]
    allow_overpicking: bool = False
    allow_partial_picking: bool = True
    auto_reserve_stock: bool = True
    require_picking_confirmation: bool = True
    default_warehouse_id: Optional[int] = None
    dolibarr_api_url: Optional[HttpUrl] = None
    dolibarr_api_key: Optional[str] = None
    dolibarr_warehouse_id: Optional[int] = None
    webhook_url: Optional[HttpUrl] = None
    notify_on_picking_complete: bool = False
    notify_on_stock_difference: bool = False
    notify_on_integration_error: bool = True
    brand_name: Optional[str] = None
    brand_logo_url: Optional[HttpUrl] = None
    brand_primary_color: Optional[str] = None
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 60


class TenantConfigCreate(TenantConfigBase):
    tenant_id: int


class TenantConfigUpdate(BaseModel):
    allow_overpicking: Optional[bool]
    allow_partial_picking: Optional[bool]
    auto_reserve_stock: Optional[bool]
    require_picking_confirmation: Optional[bool]
    default_warehouse_id: Optional[int]
    dolibarr_api_url: Optional[HttpUrl]
    dolibarr_api_key: Optional[str]
    dolibarr_warehouse_id: Optional[int]
    webhook_url: Optional[HttpUrl]
    notify_on_picking_complete: Optional[bool]
    notify_on_stock_difference: Optional[bool]
    notify_on_integration_error: Optional[bool]
    brand_name: Optional[str]
    brand_logo_url: Optional[HttpUrl]
    brand_primary_color: Optional[str]
    max_retry_attempts: Optional[int]
    retry_delay_seconds: Optional[int]


class TenantConfigResponse(TenantConfigBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True


class IntegrationStatus(BaseModel):
    is_connected: bool
    config_ok: bool
    dolibarr_api_url: bool
    dolibarr_api_key: bool
    webhook_url: bool
    pending_operations: int
    error_count: int
    last_sync: Optional[datetime]
    connection_test: Optional[dict] = None
