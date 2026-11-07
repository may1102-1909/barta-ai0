from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.order_service import OrderService

router = APIRouter(prefix="/order-form", tags=["Public Order Details Form"])

class OrderFormSubmit(BaseModel):
    customer_name: str
    address: str
    city: str
    state: str
    pincode: str
    payment_method: str = "cod" # cod or razorpay

@router.get("/{token}")
async def get_order_form_data(token: str, db: AsyncSession = Depends(get_db)):
    """
    Public endpoint for customers to view reserved order summary.
    """
    order_data = await OrderService.get_order_by_token(token, db)
    if not order_data:
        raise HTTPException(status_code=404, detail="Order link invalid or expired.")
    if "error" in order_data:
        raise HTTPException(status_code=400, detail=order_data["message"])
    return order_data

@router.post("/{token}")
async def submit_order_form(
    token: str,
    payload: OrderFormSubmit,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint for customer to submit delivery address & payment option.
    """
    if not payload.pincode or len(payload.pincode.strip()) < 6:
        raise HTTPException(status_code=400, detail="Please enter a valid 6-digit Indian PIN code.")

    order = await OrderService.complete_order(
        token=token,
        customer_name=payload.customer_name,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        pincode=payload.pincode,
        payment_method=payload.payment_method,
        db=db
    )
    if not order:
        raise HTTPException(status_code=400, detail="Order link invalid, expired, or already completed.")

    return {
        "status": "success",
        "message": "Delivery details received successfully!",
        "order_id": order.id,
        "payment_method": order.payment_method,
        "order_status": order.status
    }

