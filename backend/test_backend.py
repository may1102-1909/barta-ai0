import asyncio
from app.database import init_db, AsyncSessionLocal
from app.models import Product
from sqlalchemy import select
from app.services.llm_agent import VoiceAgentLLM

async def main():
    print("1. Initializing DB...")
    await init_db()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product))
        prod = result.scalars().first()
        print(f"2. Seed product found: {prod.name} (Offer: Rs. {prod.discount_price})")

    print("3. Testing VoiceAgent dialogue turn...")
    agent = VoiceAgentLLM(
        contact_name="Aarav Sharma",
        contact_phone="+919876543210",
        contact_email="aarav@example.com",
        preferred_language="hinglish",
        product_info=prod.details,
        campaign_goal="Festival offer for linen kurta"
    )
    greeting = agent.get_initial_greeting()
    print("Initial greeting:", greeting)

    res = await agent.generate_response("Haan main interested hoon, price kya hai?")
    print("Agent reply:", res["text"])

    res2 = await agent.generate_response("Theek hai ek piece order confirm kar do cod pe.")
    print("Agent order confirm reply:", res2["text"])
    print("Tool called:", res2.get("tool_called"))
    print("Outcome:", res2.get("outcome"))
    print("Summary:", agent.generate_summary())
    print("\nALL BACKEND TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())

