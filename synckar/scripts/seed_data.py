"""
Seed synthetic test data into all 3 mock systems.
All UBIDs use the KA-TEST-XXXXX format (AGENTS.md §15: synthetic data only).

Distribution:
  - 15 businesses in ALL 3 systems (SWS + Shop + Factories)
  - 3 businesses in SWS + Shop only (to test Factories UBID_NOT_FOUND skip)
  - 2 businesses in SWS only (to test both depts UBID_NOT_FOUND skip)
"""

import httpx
import sys
import time

# Default URLs — override with env vars if deployed
SWS_URL = "http://localhost:8000"
SHOP_URL = "http://localhost:8001"
FACTORIES_URL = "http://localhost:8002"


def generate_businesses():
    """Generate 20 synthetic businesses."""
    businesses = []
    for i in range(1, 21):
        ubid = f"KA-TEST-{i:04d}"
        businesses.append({
            "ubid": ubid,
            "business_name": f"Test Business {i} Pvt Ltd",
            "registered_address": f"{100 + i} MG Road, Bangalore 560{i:03d}",
            "primary_contact": f"+91-80-{4000 + i:04d}-{1000 + i:04d}",
            "authorized_signatory": f"Signatory Person {i}",
            "employee_headcount": 10 + i * 5,
            "operational_status": "active",
            "license_status": "valid",
            "safety_clearance": "approved",
            "last_inspection_date": f"2026-0{min(i, 9)}-15",
        })
    return businesses


def seed_sws(businesses: list[dict], base_url: str) -> int:
    """Seed all 20 businesses into mock SWS."""
    with httpx.Client(base_url=base_url, timeout=10) as client:
        sws_records = []
        for biz in businesses:
            sws_records.append(biz)

        resp = client.post("/api/businesses/batch", json=sws_records)
        resp.raise_for_status()
        result = resp.json()
        print(f"  SWS: seeded {result['created']} businesses")
        return result["created"]


def seed_shop(businesses: list[dict], base_url: str) -> int:
    """Seed first 18 businesses into mock Shop Establishment (15 + 3)."""
    with httpx.Client(base_url=base_url, timeout=10) as client:
        shop_records = []
        for i, biz in enumerate(businesses[:18]):
            shop_records.append({
                "shop_reg_no": f"SHOP-{i + 1:04d}",
                "ubid": biz["ubid"],
                "business_name": biz["business_name"],
                "Buss_Addr_Line1": biz["registered_address"],
                "Contact_Phone": biz["primary_contact"],
                "Auth_Sign_Name": biz["authorized_signatory"],
                "Emp_Count": biz["employee_headcount"],
                "Op_Status": biz["operational_status"],
                "Lic_Status": biz["license_status"],
            })

        resp = client.post("/api/records/batch", json=shop_records)
        resp.raise_for_status()
        result = resp.json()
        print(f"  Shop Establishment: seeded {result['created']} records")
        return result["created"]


def seed_factories(businesses: list[dict], base_url: str) -> int:
    """Seed first 15 businesses into mock Factories."""
    with httpx.Client(base_url=base_url, timeout=10) as client:
        factory_records = []
        for i, biz in enumerate(businesses[:15]):
            factory_records.append({
                "factory_license_no": f"FACT-{i + 1:04d}",
                "ubid": biz["ubid"],
                "business_name": biz["business_name"],
                "factory_address": biz["registered_address"],
                "contact_number": biz["primary_contact"],
                "signatory_name": biz["authorized_signatory"],
                "worker_count": biz["employee_headcount"],
                "factory_status": biz["operational_status"],
                "lic_status": biz["license_status"],
                "safety_cert": biz["safety_clearance"],
                "labor_violations": "none",
                "last_inspection_date": biz["last_inspection_date"],
            })

        resp = client.post("/api/records/batch", json=factory_records)
        resp.raise_for_status()
        result = resp.json()
        print(f"  Factories: seeded {result['created']} records")
        return result["created"]


def wait_for_services(max_retries: int = 30, delay: float = 2.0):
    """Wait until all mock services are healthy."""
    services = [
        ("SWS", SWS_URL),
        ("Shop Est", SHOP_URL),
        ("Factories", FACTORIES_URL),
    ]
    for name, url in services:
        for attempt in range(max_retries):
            try:
                resp = httpx.get(f"{url}/health", timeout=3)
                if resp.status_code == 200:
                    print(f"  {name} is healthy")
                    break
            except httpx.ConnectError:
                pass
            if attempt == max_retries - 1:
                print(f"  ERROR: {name} not reachable at {url}")
                sys.exit(1)
            time.sleep(delay)


def main():
    global SWS_URL, SHOP_URL, FACTORIES_URL

    # Allow base URL override from CLI args
    if len(sys.argv) > 1:
        SWS_URL = sys.argv[1]
    if len(sys.argv) > 2:
        SHOP_URL = sys.argv[2]
    if len(sys.argv) > 3:
        FACTORIES_URL = sys.argv[3]

    print("SyncKar — Seeding synthetic test data")
    print(f"  SWS:       {SWS_URL}")
    print(f"  Shop Est:  {SHOP_URL}")
    print(f"  Factories: {FACTORIES_URL}")
    print()

    print("Waiting for services...")
    wait_for_services()
    print()

    businesses = generate_businesses()

    print("Seeding data...")
    seed_sws(businesses, SWS_URL)
    seed_shop(businesses, SHOP_URL)
    seed_factories(businesses, FACTORIES_URL)

    print()
    print("Seed complete:")
    print("  20 businesses in SWS (all)")
    print("  18 businesses in Shop Establishment (KA-TEST-0001 to KA-TEST-0018)")
    print("  15 businesses in Factories (KA-TEST-0001 to KA-TEST-0015)")
    print("  KA-TEST-0016 to KA-TEST-0018: SWS + Shop only (Factories UBID_NOT_FOUND)")
    print("  KA-TEST-0019 to KA-TEST-0020: SWS only (both depts UBID_NOT_FOUND)")


if __name__ == "__main__":
    main()
