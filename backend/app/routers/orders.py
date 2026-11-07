from typing import Optional
from datetime import datetime
import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Order, Product, Contact
from app.config import settings

router = APIRouter(prefix="/orders", tags=["Orders"])
IST = pytz.timezone("Asia/Kolkata")

@router.get("")
async def list_orders(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Order).order_by(desc(Order.created_at)).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Order.status == status)

    result = await db.execute(stmt)
    orders = result.scalars().all()

    output = []
    for ord in orders:
        prod_res = await db.execute(select(Product).where(Product.id == ord.product_id))
        product = prod_res.scalars().first()

        created_at_ist = None
        if ord.created_at:
            created_at_ist = ord.created_at.replace(tzinfo=pytz.utc).astimezone(IST).strftime("%d %b %Y, %I:%M %p IST")

        price = (product.discount_price if product and product.discount_price else (product.price if product else 1499.0)) * ord.quantity

        form_url = f"{settings.FRONTEND_URL}/order-form/{ord.form_token}"

        output.append({
            "id": ord.id,
            "product_name": product.name if product else "CURATED Linen Kurta",
            "quantity": ord.quantity,
            "total_price": price,
            "status": ord.status,
            "customer_name": ord.customer_name,
            "customer_email": ord.customer_email,
            "customer_phone": ord.customer_phone,
            "delivery_address": f"{ord.address or ''}, {ord.city or ''} - {ord.pincode or ''}".strip(" ,-"),
            "payment_method": ord.payment_method,
            "form_url": form_url,
            "created_at_ist": created_at_ist,
            "form_expires_at": ord.form_expires_at.isoformat() if ord.form_expires_at else None
        })

    return output

@router.get("/{order_id}")
async def get_order_detail(order_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    prod_res = await db.execute(select(Product).where(Product.id == order.product_id))
    product = prod_res.scalars().first()

    return {
        "order": order,
        "product": product,
        "form_url": f"{settings.FRONTEND_URL}/order-form/{order.form_token}"
    }

