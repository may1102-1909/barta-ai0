import asyncio
import httpx
from datetime import datetime

async def test_full_pipeline():
    print("==================================================")
    print("  BARTA AI: FULL END-TO-END ACCEPTANCE TEST")
    print("==================================================")

    # Use ASGITransport to test FastAPI without needing an external port binding
    from app.main import app
    from app.database import init_db
    
    await init_db()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Health check
        print("\n[STEP 1] Testing Health & Diagnostics...")
        res = await client.get("/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("  ✓ Health Check Passed:", res.json())

        # 2. Create Campaign
        print("\n[STEP 2] Creating Festival Outbound Campaign...")
        camp_res = await client.post("/campaigns", json={
            "name": "E2E CURATED Festive Kurta Drive",
            "goal": "Introduce CURATED Minimalist Linen Kurta festival offer and book orders.",
            "max_concurrent": 1,
            "window_start": "09:00",
            "window_end": "21:00",
            "retry_limit": 2
        })
        assert camp_res.status_code == 200, f"Create campaign failed: {camp_res.text}"
        campaign = camp_res.json()
        campaign_id = campaign["id"]
        print(f"  ✓ Campaign Created: ID={campaign_id}, Name={campaign['name']}")

        # 3. Import Contacts CSV
        print("\n[STEP 3] Importing Customer Contacts CSV...")
        with open("backend/data/sample_contacts.csv", "rb") as f:
            csv_bytes = f.read()
        
        files = {"file": ("sample_contacts.csv", csv_bytes, "text/csv")}
        import_res = await client.post(f"/campaigns/{campaign_id}/contacts/import", files=files)
        assert import_res.status_code == 200, f"CSV import failed: {import_res.text}"
        import_data = import_res.json()
        print(f"  ✓ Contacts Imported: {import_data['imported_count']} valid contacts, {import_data['rejected_count']} rejected.")
        assert import_data["imported_count"] >= 5

        # 4. Start Simulated Voice Call
        print("\n[STEP 4] Initiating Simulated Voice Call (Gnani Prisma + Timbre + Gemini)...")
        sim_start_res = await client.post("/simulator/start", json={
            "contact_name": "Aarav Sharma",
            "contact_phone": "+919876543210",
            "contact_email": "aarav.sharma@example.com",
            "preferred_language": "hinglish",
            "campaign_id": campaign_id
        })
        assert sim_start_res.status_code == 200, f"Simulator start failed: {sim_start_res.text}"
        sim_data = sim_start_res.json()
        session_id = sim_data["session_id"]
        call_id = sim_data["call_id"]
        print(f"  ✓ Call Connected (ID={call_id})")
        print(f"  Agent Initial Greeting: \"{sim_data['greeting']}\"")
        assert "BARTA" in sim_data["greeting"]

        # 5. Customer asks for price & discount
        print("\n[STEP 5] Spoken Turn 1: Customer asks about pricing and festive offer...")
        turn1_res = await client.post("/simulator/turn", json={
            "session_id": session_id,
            "user_transcript": "Haan main interested hoon, price kya hai aur koi discount hai kya?"
        })
        assert turn1_res.status_code == 200
        t1 = turn1_res.json()
        print(f"  Agent Voice Reply: \"{t1['agent_reply']}\"")
        assert "1499" in t1["agent_reply"] or "offer" in t1["agent_reply"].lower()

        # 6. Customer confirms order
        print("\n[STEP 6] Spoken Turn 2: Customer confirms order on Cash on Delivery...")
        turn2_res = await client.post("/simulator/turn", json={
            "session_id": session_id,
            "user_transcript": "Great! Ek piece order book kar do Cash on Delivery pe."
        })
        assert turn2_res.status_code == 200
        t2 = turn2_res.json()
        print(f"  Agent Voice Reply: \"{t2['agent_reply']}\"")
        print(f"  ✓ Tool Invoked: {t2.get('tool_called')}")
        print(f"  ✓ Outcome Recorded: {t2.get('outcome')}")
        assert t2.get("tool_called") == "confirm_order"
        assert t2.get("outcome") == "order_confirmed"

        # 7. Verify Call Details in DB
        print("\n[STEP 7] Verifying Saved Call Transcript & Summary...")
        call_detail_res = await client.get(f"/calls/{call_id}")
        assert call_detail_res.status_code == 200
        call_obj = call_detail_res.json()
        print(f"  ✓ Call Status: {call_obj['status']}")
        print(f"  ✓ Final Outcome: {call_obj['outcome']}")
        print(f"  ✓ AI Summary: {call_obj['summary']}")
        print(f"  ✓ Transcript Turns: {len(call_obj['transcript'])} dialogue entries")
        assert call_obj["outcome"] == "order_confirmed"

        # 8. Verify Order Creation & Secure Form Link
        print("\n[STEP 8] Verifying Created Order & Secure Token...")
        orders_res = await client.get("/orders")
        assert orders_res.status_code == 200
        orders_list = orders_res.json()
        assert len(orders_list) > 0
        latest_order = orders_list[0]
        print(f"  ✓ Order ID: {latest_order['id']}")
        print(f"  ✓ Customer: {latest_order['customer_name']} ({latest_order['customer_email']})")
        print(f"  ✓ Product: {latest_order['product_name']} (Total: ₹{latest_order['total_price']})")
        print(f"  ✓ Order Status: {latest_order['status']}")
        print(f"  ✓ Hosted Form URL: {latest_order['form_url']}")
        assert latest_order["status"] == "awaiting_details"
        token = latest_order["form_url"].split("/order-form/")[-1]

        # 9. Verify Public Hosted Order Form Page
        print("\n[STEP 9] Fetching Public Order Form Page via Token...")
        form_get_res = await client.get(f"/order-form/{token}")
        assert form_get_res.status_code == 200
        form_data = form_get_res.json()
        print(f"  ✓ Form Verified: Product='{form_data['product_name']}', Price=₹{form_data['price']}")

        # 10. Customer Submits Delivery Address & Payment Choice
        print("\n[STEP 10] Customer Submits Address and Selects Cash on Delivery...")
        submit_res = await client.post(f"/order-form/{token}", json={
            "customer_name": "Aarav Sharma",
            "address": "Flat 304, Palm Grove Heights, Indiranagar",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560038",
            "payment_method": "cod"
        })
        assert submit_res.status_code == 200
        submit_data = submit_res.json()
        print(f"  ✓ Form Submission Response: {submit_data['message']}")
        print(f"  ✓ Updated Order Status: {submit_data['order_status']}")
        assert submit_data["order_status"] == "cod"

        # 11. Test Callback Scheduling Turn
        print("\n[STEP 11] Testing Callback Turn on second contact...")
        sim2_res = await client.post("/simulator/start", json={
            "contact_name": "Priya Patel",
            "contact_phone": "+919876543211",
            "contact_email": "priya.patel@example.com",
            "preferred_language": "hindi",
            "campaign_id": campaign_id
        })
        sim2_data = sim2_res.json()
        sim2_session = sim2_data["session_id"]
        sim2_call_id = sim2_data["call_id"]

        cb_turn_res = await client.post("/simulator/turn", json={
            "session_id": sim2_session,
            "user_transcript": "Main abhi meeting me hoon, mujhe kal dopahar me 2 baje call karo."
        })
        assert cb_turn_res.status_code == 200
        cb_res_data = cb_turn_res.json()
        print(f"  Agent Callback Voice Reply: \"{cb_res_data['agent_reply']}\"")
        print(f"  ✓ Tool Invoked: {cb_res_data.get('tool_called')}")
        print(f"  ✓ Outcome Recorded: {cb_res_data.get('outcome')}")
        assert cb_res_data.get("tool_called") == "schedule_callback"

        # Verify callback in database
        callbacks_res = await client.get("/callbacks")
        assert callbacks_res.status_code == 200
        cb_list = callbacks_res.json()
        assert len(cb_list) > 0
        latest_cb = cb_list[0]
        print(f"  ✓ Callback in Queue: Due={latest_cb['due_at_ist']}, Status={latest_cb['status']}")

        # 12. Check Funnel Stats
        print("\n[STEP 12] Checking Updated Campaign Funnel & Dashboard Counters...")
        stats_res = await client.get(f"/campaigns/{campaign_id}/stats")
        assert stats_res.status_code == 200
        stats_obj = stats_res.json()
        print("  ✓ Funnel:", stats_obj["funnel"])
        print("  ✓ Counters:", stats_obj["counters"])
        assert stats_obj["counters"]["total_calls"] >= 2
        assert stats_obj["counters"]["orders_confirmed"] >= 1

    print("\n==================================================")
    print("  🏆 ALL 12 END-TO-END PIPELINE CHECKS PASSED! 🏆")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())

