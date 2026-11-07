import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from app.config import settings
from app.models import Base, Product, generate_uuid, utc_now

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    # Seed demo product if none exists
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product))
        product = result.scalars().first()
        if not product:
            demo_product = Product(
                id="curated-linen-kurta-01",
                name="CURATED Minimalist Linen Kurta",
                description="Handcrafted breathable pure linen kurta in earthy tones. Tailored for effortless comfort, festive gatherings, and modern everyday Indian living.",
                price=1899.0,
                discount_price=1499.0,
                url="https://curatedindia.vercel.app",
                details={
                    "brand": "CURATED India",
                    "fabric": "100% Organic Handspun Linen",
                    "available_sizes": ["S", "M", "L", "XL", "XXL"],
                    "available_colors": ["Natural Ivory", "Sage Olive", "Charcoal Slate", "Earthy Ochre"],
                    "discount_offer": "Exclusive festival offer: Flat ₹400 OFF today (Offer Price: ₹1,499)",
                    "shipping": "Free express delivery across India (3-5 business days)",
                    "returns": "7-day hassle-free exchange & returns",
                    "payment_options": ["Cash on Delivery (COD)", "UPI / Card Online"]
                }
            )
            session.add(demo_product)
            await session.commit()
            print("Successfully initialized DB and seeded CURATED demo product.")

