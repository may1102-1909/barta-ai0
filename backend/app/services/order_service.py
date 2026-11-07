import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Order, Contact, Product, Message
from app.config import settings
from app.services.email_service import EmailService

class OrderService:

    @staticmethod
    async def create_order_from_call(
        contact_id: str,
        call_id: Optional[str],
        product_id: str,
        quantity: int,
        email: str,
        db: AsyncSession
    ) -> Order:
        """
        Creates an order with awaiting_details status, generates a secure 72h token,
        and triggers the delivery details email.
        """
        # Fetch contact & product
        contact_res = await db.execute(select(Contact).where(Contact.id == contact_id))
        contact = contact_res.scalars().first()

        product_res = await db.execute(select(Product).where(Product.id == product_id))
        product = product_res.scalars().first()
        if not product:
            # fallback to default first product
            product_all = await db.execute(select(Product))
            product = product_all.scalars().first()

        form_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=72)

        order = Order(
            contact_id=contact_id,
            call_id=call_id,
            product_id=product.id if product else "default",
            quantity=max(1, quantity),
            status="awaiting_details",
            form_token=form_token,
            form_expires_at=expires_at,
            customer_name=contact.name if contact else "Valued Customer",
            customer_email=email,
            customer_phone=contact.phone if contact else ""
        )
        db.add(order)

        # Update contact email if missing
        if contact and not contact.email:
            contact.email = email

        await db.commit()
        await db.refresh(order)

        # Construct public form URL
        form_url = f"{settings.FRONTEND_URL}/order-form/{form_token}"

        # Send order details email
        price = product.discount_price if (product and product.discount_price) else (product.price if product else 1499.0)
        prod_name = product.name if product else "CURATED Linen Kurta"
        cust_name = contact.name if contact else "Customer"

        await EmailService.send_order_form_email(
            to_email=email,
            customer_name=cust_name,
            product_name=prod_name,
            price=price * quantity,
            form_url=form_url
        )

        # Record email message
        msg = Message(
            contact_id=contact_id,
            channel="email",
            direction="outbound",
            body=f"Sent order form link for {prod_name} to {email}",
            status="sent"
        )
        db.add(msg)
        await db.commit()

        return order

    @staticmethod
    async def get_order_by_token(token: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """Validates token, checks expiry, and returns order with product details."""
        result = await db.execute(select(Order).where(Order.form_token == token))
        order = result.scalars().first()
        if not order:
            return None

        # Check expiry
        now_utc = datetime.now(timezone.utc)
        expires_at = order.form_expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at and expires_at < now_utc:
            return {"error": "expired", "message": "This order link has expired after 72 hours."}

        # Check if already completed
        if order.status not in ["awaiting_details"]:
            return {"error": "already_submitted", "message": "This order details form has already been submitted."}

        # Fetch product
        prod_res = await db.execute(select(Product).where(Product.id == order.product_id))
        product = prod_res.scalars().first()

        price = (product.discount_price if product and product.discount_price else (product.price if product else 1499.0)) * order.quantity

        return {
            "order_id": order.id,
            "product_name": product.name if product else "CURATED Minimalist Linen Kurta",
            "quantity": order.quantity,
            "price": price,
            "customer_name": order.customer_name,
            "customer_email": order.customer_email,
            "customer_phone": order.customer_phone,
            "status": order.status,
            "expires_at": order.form_expires_at.isoformat()
        }

    @staticmethod
    async def complete_order(
        token: str,
        customer_name: str,
        address: str,
        city: str,
        state: str,
        pincode: str,
        payment_method: str,
        db: AsyncSession
    ) -> Optional[Order]:
        """Saves delivery details and marks order as details_received / paid / cod."""
        result = await db.execute(select(Order).where(Order.form_token == token))
        order = result.scalars().first()
        if not order or order.status != "awaiting_details":
            return None

        order.customer_name = customer_name
        order.address = address
        order.city = city
        order.state = state
        order.pincode = pincode
        order.payment_method = payment_method

        if payment_method == "razorpay":
            order.status = "paid"
        elif payment_method == "cod":
            order.status = "cod"
        else:
            order.status = "details_received"

        await db.commit()
        await db.refresh(order)
        return order
