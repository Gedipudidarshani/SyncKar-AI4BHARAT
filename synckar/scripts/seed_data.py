"""
Seed synthetic test data into all 3 mock systems.
Uses realistic Karnataka business names for demo narrative.

Distribution:
  - 15 businesses in ALL 3 systems (SWS + Shop + Factories)
  - 3 businesses in SWS + Shop only (KA-TEST-0016 to KA-TEST-0018)
  - 2 businesses in SWS only (KA-TEST-0019 to KA-TEST-0020)
"""

import httpx
import os
import sys
import time

SWS_URL = os.environ.get("SWS_URL") or os.environ.get(
    "MOCK_SWS_BASE_URL", "http://localhost:8000/sws"
)
SHOP_URL = os.environ.get("SHOP_URL") or os.environ.get(
    "MOCK_SHOP_BASE_URL", "http://localhost:8000/shop"
)
FACTORIES_URL = os.environ.get("FACTORIES_URL") or os.environ.get(
    "MOCK_FACTORIES_BASE_URL", "http://localhost:8000/factories"
)

# Realistic Karnataka business data for demo narrative
BUSINESSES = [
    {
        "ubid": "KA-TEST-0001",
        "business_name": "Bengaluru Silk Weavers Pvt Ltd",
        "registered_address": "14 Cunningham Road, Bengaluru 560052",
        "primary_contact": "+91-80-4112-3456",
        "authorized_signatory": "Rajesh Kumar Sharma",
        "employee_headcount": 85,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-01-15",
    },
    {
        "ubid": "KA-TEST-0002",
        "business_name": "Mysuru Agro Industries Ltd",
        "registered_address": "Plot 22, KIADB Industrial Area, Mysuru 570016",
        "primary_contact": "+91-821-2412-789",
        "authorized_signatory": "Priya Venkatesh",
        "employee_headcount": 142,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-02-10",
    },
    {
        "ubid": "KA-TEST-0003",
        "business_name": "Hubli Steel Fabricators Pvt Ltd",
        "registered_address": "Survey No. 45, Gokul Road, Hubballi 580030",
        "primary_contact": "+91-836-2234-567",
        "authorized_signatory": "Suresh Basavaraj",
        "employee_headcount": 210,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-01-28",
    },
    {
        "ubid": "KA-TEST-0004",
        "business_name": "Mangaluru Cashew Exports Ltd",
        "registered_address": "Bunder Road, Mangaluru 575001",
        "primary_contact": "+91-824-2441-234",
        "authorized_signatory": "Anitha D'Souza",
        "employee_headcount": 67,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-03-05",
    },
    {
        "ubid": "KA-TEST-0005",
        "business_name": "Dharwad Pharma Solutions Pvt Ltd",
        "registered_address": "KSSIDC Industrial Estate, Dharwad 580004",
        "primary_contact": "+91-836-2448-901",
        "authorized_signatory": "Dr. Kavitha Patil",
        "employee_headcount": 320,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-02-20",
    },
    {
        "ubid": "KA-TEST-0006",
        "business_name": "Belagavi Textile Mills Ltd",
        "registered_address": "Udyambag Industrial Area, Belagavi 590008",
        "primary_contact": "+91-831-2423-678",
        "authorized_signatory": "Mahesh Kulkarni",
        "employee_headcount": 450,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-01-10",
    },
    {
        "ubid": "KA-TEST-0007",
        "business_name": "Tumkur Auto Components Pvt Ltd",
        "registered_address": "KIADB Phase II, Tumakuru 572106",
        "primary_contact": "+91-816-2272-345",
        "authorized_signatory": "Ravi Shankar Gowda",
        "employee_headcount": 178,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-03-12",
    },
    {
        "ubid": "KA-TEST-0008",
        "business_name": "Shivamogga Paper Industries Ltd",
        "registered_address": "Bhadravathi Road, Shivamogga 577201",
        "primary_contact": "+91-8182-223456",
        "authorized_signatory": "Lakshmi Narayana",
        "employee_headcount": 290,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-02-05",
    },
    {
        "ubid": "KA-TEST-0009",
        "business_name": "Kolar Gold Jewellers Pvt Ltd",
        "registered_address": "B B Road, Kolar 563101",
        "primary_contact": "+91-8152-222789",
        "authorized_signatory": "Srinivas Reddy",
        "employee_headcount": 45,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-01-22",
    },
    {
        "ubid": "KA-TEST-0010",
        "business_name": "Raichur Power Equipment Ltd",
        "registered_address": "Industrial Area, Raichur 584101",
        "primary_contact": "+91-8532-226789",
        "authorized_signatory": "Abdul Kareem",
        "employee_headcount": 520,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-03-01",
    },
    {
        "ubid": "KA-TEST-0011",
        "business_name": "Bidar Ceramics Pvt Ltd",
        "registered_address": "Udgir Road, Bidar 585401",
        "primary_contact": "+91-8482-227890",
        "authorized_signatory": "Fatima Begum",
        "employee_headcount": 95,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-02-15",
    },
    {
        "ubid": "KA-TEST-0012",
        "business_name": "Vijayapura Sugar Mills Ltd",
        "registered_address": "Solapur Road, Vijayapura 586101",
        "primary_contact": "+91-8352-250123",
        "authorized_signatory": "Basavaraj Patil",
        "employee_headcount": 680,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-01-05",
    },
    {
        "ubid": "KA-TEST-0013",
        "business_name": "Gadag Granite Exports Pvt Ltd",
        "registered_address": "NH-67, Gadag 582101",
        "primary_contact": "+91-8372-234567",
        "authorized_signatory": "Veeranna Hiremath",
        "employee_headcount": 130,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-03-18",
    },
    {
        "ubid": "KA-TEST-0014",
        "business_name": "Koppal Iron & Steel Ltd",
        "registered_address": "Gangavathi Road, Koppal 583231",
        "primary_contact": "+91-8539-220456",
        "authorized_signatory": "Nagaraj Bellad",
        "employee_headcount": 410,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-02-28",
    },
    {
        "ubid": "KA-TEST-0015",
        "business_name": "Yadgir Cement Works Pvt Ltd",
        "registered_address": "Gulbarga Road, Yadgir 585201",
        "primary_contact": "+91-8473-221789",
        "authorized_signatory": "Chandrashekhar Rao",
        "employee_headcount": 750,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-01-30",
    },
    # SWS + Shop only (no factory)
    {
        "ubid": "KA-TEST-0016",
        "business_name": "Bengaluru IT Solutions Pvt Ltd",
        "registered_address": "Whitefield, Bengaluru 560066",
        "primary_contact": "+91-80-4567-8901",
        "authorized_signatory": "Deepa Krishnamurthy",
        "employee_headcount": 230,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-03-10",
    },
    {
        "ubid": "KA-TEST-0017",
        "business_name": "Mysuru Handicrafts Emporium",
        "registered_address": "Sayyaji Rao Road, Mysuru 570001",
        "primary_contact": "+91-821-2423-456",
        "authorized_signatory": "Geetha Nagaraj",
        "employee_headcount": 38,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-02-22",
    },
    {
        "ubid": "KA-TEST-0018",
        "business_name": "Mangaluru Seafood Processors Ltd",
        "registered_address": "Panambur, Mangaluru 575010",
        "primary_contact": "+91-824-2456-789",
        "authorized_signatory": "Peter Fernandes",
        "employee_headcount": 165,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-01-18",
    },
    # SWS only
    {
        "ubid": "KA-TEST-0019",
        "business_name": "Bengaluru Fintech Ventures Pvt Ltd",
        "registered_address": "Koramangala, Bengaluru 560034",
        "primary_contact": "+91-80-4890-1234",
        "authorized_signatory": "Arun Mehta",
        "employee_headcount": 55,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-03-20",
    },
    {
        "ubid": "KA-TEST-0020",
        "business_name": "Karnataka Organic Farms Ltd",
        "registered_address": "Hesaraghatta Road, Bengaluru 560088",
        "primary_contact": "+91-80-2846-5678",
        "authorized_signatory": "Savitha Gowda",
        "employee_headcount": 42,
        "operational_status": "active",
        "license_status": "valid",
        "safety_clearance": "approved",
        "last_inspection_date": "2026-02-08",
    },
]


def seed_sws(businesses, base_url):
    with httpx.Client(base_url=base_url, timeout=10) as client:
        resp = client.post("/api/businesses/batch", json=businesses)
        resp.raise_for_status()
        result = resp.json()
        print(f"  SWS: seeded {result['created']} businesses")
        return result["created"]


def seed_shop(businesses, base_url):
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


def seed_factories(businesses, base_url):
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


def wait_for_services(max_retries=30, delay=2.0):
    services = [("SWS", SWS_URL), ("Shop Est", SHOP_URL), ("Factories", FACTORIES_URL)]
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
    if len(sys.argv) > 1: SWS_URL = sys.argv[1]
    if len(sys.argv) > 2: SHOP_URL = sys.argv[2]
    if len(sys.argv) > 3: FACTORIES_URL = sys.argv[3]

    print("SyncKar — Seeding synthetic test data")
    print(f"  SWS:       {SWS_URL}")
    print(f"  Shop Est:  {SHOP_URL}")
    print(f"  Factories: {FACTORIES_URL}")
    print()
    print("Waiting for services...")
    wait_for_services()
    print()
    print("Seeding data...")
    seed_sws(BUSINESSES, SWS_URL)
    seed_shop(BUSINESSES, SHOP_URL)
    seed_factories(BUSINESSES, FACTORIES_URL)
    print()
    print("Seed complete:")
    print("  20 businesses in SWS (all)")
    print("  18 businesses in Shop Establishment (KA-TEST-0001 to KA-TEST-0018)")
    print("  15 businesses in Factories (KA-TEST-0001 to KA-TEST-0015)")
    print("  KA-TEST-0016 to KA-TEST-0018: SWS + Shop only (Factories UBID_NOT_FOUND)")
    print("  KA-TEST-0019 to KA-TEST-0020: SWS only (both depts UBID_NOT_FOUND)")


if __name__ == "__main__":
    main()
