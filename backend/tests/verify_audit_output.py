import sys
import httpx

sys.stdout.reconfigure(encoding='utf-8')

# 1. Create a session
s_res = httpx.post("http://127.0.0.1:8000/session")
session_id = s_res.json()["session_id"]

# 2. Add TitanFold Wallet to cart
httpx.post(f"http://127.0.0.1:8000/session/{session_id}/cart/items", json={"product_id": 6, "qty": 1})

# 3. Chat: ask for recommendation
httpx.post(f"http://127.0.0.1:8000/session/{session_id}/message", json={"message": "Can you suggest an accessory?"})

# 4. Chat: ask for 35% discount (modified to 20%)
httpx.post(f"http://127.0.0.1:8000/session/{session_id}/message", json={"message": "Can you do 35% discount?"})

# 5. Checkout
httpx.post(f"http://127.0.0.1:8000/session/{session_id}/checkout")

# 6. Query audit feed
r = httpx.get(f"http://127.0.0.1:8000/audit/{session_id}")
data = r.json()

print("Status:", r.status_code)
print("Summary:", data["summary"])
print("\n--- DECISION LEDGER TIMELINE ---")
for e in data["timeline"]:
    print(f"{e['time_str']} | {e['action']:10} | {e['summary']:28} | {e['decision'].upper():8} | {e['rule_triggered']}")
