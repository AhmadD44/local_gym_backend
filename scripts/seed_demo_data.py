"""One-off CLI to fill a running deployment with realistic demo data —
gym settings, trainers, members, plans, exercises, workouts, classes, a
store catalog with a promotion, an order, and progress/water/nutrition
logs — driving the live REST API exactly as the Flutter app would (never
inserting rows directly), so every response the app will actually see is
exercised: image resize/upload, ownership checks, capacity locks, cart
pricing, etc.

The one exception is bootstrapping admin access: there is no public API
path to become an admin, so this script resets the existing bootstrap
admin's (admin@example.com) password directly in the database to a known
value, then logs in normally like everything else.

Usage:
    python -m scripts.seed_demo_data

Env vars:
    SEED_BASE_URL       default: the live Render deployment
    SEED_DATABASE_URL   default: same Neon connection used elsewhere in this session
    SEED_ADMIN_PASSWORD default: Seed-Admin-2026!
"""

import io
import os
import random
import time
from datetime import UTC, datetime, timedelta

import asyncpg
import httpx
from argon2 import PasswordHasher
from PIL import Image, ImageDraw, ImageFont

BASE_URL = os.environ.get("SEED_BASE_URL", "https://local-gym-backend.onrender.com/api/v1")
DATABASE_URL = os.environ.get(
    "SEED_DATABASE_URL",
    "postgresql://neondb_owner:npg_vpVq9eB7zRkh@ep-shiny-glade-aek71uqp-pooler.c-2.us-east-2.aws.neon.tech/neondb?ssl=require",
)
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "Seed-Admin-2026!")
DEMO_PASSWORD = "Demo-Pass-2026!"

_PALETTE = [
    (198, 93, 39), (46, 125, 158), (63, 143, 92), (139, 92, 246),
    (184, 121, 31), (220, 69, 69), (37, 99, 235), (22, 163, 74),
]


def make_image(label: str, seed: int) -> bytes:
    """Synthetic placeholder photo: solid color + centered label, ~1600x1200
    (bigger than the server's 1200px cap, so the resize path is exercised)."""
    color = _PALETTE[seed % len(_PALETTE)]
    img = Image.new("RGB", (1600, 1200), color=color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arialbd.ttf", 72)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((1600 - w) / 2, (1200 - h) / 2), label, fill=(255, 255, 255), font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def reset_admin_password() -> None:
    import asyncio

    async def _run() -> None:
        hashed = PasswordHasher().hash(ADMIN_PASSWORD)
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            result = await conn.execute(
                "UPDATE users SET hashed_password = $1 WHERE email = $2", hashed, ADMIN_EMAIL
            )
            print(f"[db] reset {ADMIN_EMAIL} password: {result}")
        finally:
            await conn.close()

    asyncio.run(_run())


class Seeder:
    def __init__(self) -> None:
        self.c = httpx.Client(base_url=BASE_URL, timeout=60)

    # ---- auth helpers ----
    def login(self, email: str, password: str) -> str:
        r = self.c.post("/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        return r.json()["access_token"]

    def auth(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def upload(self, token: str, path: str, image_bytes: bytes, filename: str = "photo.jpg") -> dict:
        r = self.c.post(
            path, headers=self.auth(token), files={"file": (filename, image_bytes, "image/jpeg")}
        )
        r.raise_for_status()
        return r.json()

    # ---- domains ----
    def gym_info(self, admin: str) -> None:
        self.c.patch(
            "/gym/settings",
            headers=self.auth(admin),
            json={
                "name": "Iron Forge Gym",
                "description": "A community strength & conditioning gym with classes, coaching, and a members' store.",
                "phone": "+1 555-0142",
                "email": "hello@ironforgegym.example",
                "address": "482 Foundry Street, Springvale",
            },
        ).raise_for_status()
        hours = [
            (0, "06:00:00", "22:00:00", False), (1, "06:00:00", "22:00:00", False),
            (2, "06:00:00", "22:00:00", False), (3, "06:00:00", "22:00:00", False),
            (4, "06:00:00", "21:00:00", False), (5, "08:00:00", "18:00:00", False),
            (6, "08:00:00", "16:00:00", False),
        ]
        for day, open_t, close_t, closed in hours:
            self.c.put(
                "/gym/opening-hours",
                headers=self.auth(admin),
                json={"day_of_week": day, "open_time": open_t, "close_time": close_t, "is_closed": closed},
            ).raise_for_status()
        rules = [
            "Re-rack weights after every set.",
            "Wipe down equipment after use.",
            "Closed-toe athletic shoes required on the gym floor.",
            "Guests must sign in at the front desk.",
        ]
        for i, title in enumerate(rules):
            self.c.post(
                "/gym/rules", headers=self.auth(admin),
                json={"title": title, "description": title, "order_index": i},
            ).raise_for_status()
        faqs = [
            ("Do I need to book classes in advance?", "Yes — book through the app; spots are limited and confirmed first-come, first-served."),
            ("How do I pay for a membership?", "Memberships are confirmed in person with cash at the front desk after you subscribe in the app."),
            ("Can I freeze my membership?", "Contact the front desk — freezes are handled manually by an admin."),
            ("Is parking available?", "Yes, free parking is available in the lot behind the building."),
        ]
        for i, (q, a) in enumerate(faqs):
            self.c.post(
                "/faqs", headers=self.auth(admin),
                json={"question": q, "answer": a, "order_index": i, "is_active": True},
            ).raise_for_status()
        print("[seed] gym info done")

    def trainers(self, admin: str) -> list[dict]:
        roster = [
            ("alex.rivera@ironforgegym.example", "Alex Rivera", "Strength & conditioning coach focused on powerlifting fundamentals.", "Strength & Conditioning", 8),
            ("priya.nathan@ironforgegym.example", "Priya Nathan", "Yoga and mobility instructor, ex-competitive gymnast.", "Yoga & Mobility", 5),
            ("marcus.chen@ironforgegym.example", "Marcus Chen", "HIIT coach and nutrition specialist.", "HIIT & Nutrition Coaching", 10),
        ]
        out = []
        for i, (email, name, bio, spec, years) in enumerate(roster):
            r = self.c.post(
                "/admin/staff", headers=self.auth(admin),
                json={"email": email, "password": DEMO_PASSWORD, "full_name": name, "role": "TRAINER"},
            )
            r.raise_for_status()
            token = self.login(email, DEMO_PASSWORD)
            prof = self.c.patch(
                "/trainers/me", headers=self.auth(token),
                json={"full_name": name, "bio": bio, "specialization": spec, "years_experience": years},
            )
            prof.raise_for_status()
            photo = self.upload(token, "/trainers/me/photo", make_image(name.split()[0], i))
            out.append({"email": email, "token": token, "id": photo["id"], "name": name})
            print(f"[seed] trainer {name} -> {photo['id']}")
        return out

    def plans(self, admin: str) -> list[dict]:
        roster = [
            ("Monthly Basic", "Full gym floor access, no class booking.", 30, "29.99"),
            ("Quarterly Pro", "Gym floor + unlimited class bookings.", 90, "79.99"),
            ("Annual Elite", "Everything in Pro plus 2 free PT sessions/month.", 365, "299.99"),
        ]
        out = []
        for name, desc, days, price in roster:
            r = self.c.post(
                "/memberships/plans", headers=self.auth(admin),
                json={"name": name, "description": desc, "duration_days": days, "price": price},
            )
            r.raise_for_status()
            out.append(r.json())
        print(f"[seed] {len(out)} membership plans")
        return out

    def members(self, batch: list[str]) -> list[dict]:
        """Registers one batch of members (respects the 3/min register rate limit
        by being called in small batches with a sleep between calls)."""
        out = []
        for i, name in enumerate(batch):
            email = f"{name.lower().replace(' ', '.')}@example.com"
            r = self.c.post(
                "/auth/register", json={"email": email, "password": DEMO_PASSWORD, "full_name": name}
            )
            r.raise_for_status()
            token = r.json()["access_token"]
            prof = self.c.patch(
                "/members/me", headers=self.auth(token),
                json={
                    "full_name": name,
                    "date_of_birth": f"{random.randint(1985, 2003)}-0{random.randint(1,9)}-1{random.randint(0,9)}",
                    "phone": f"+1 555-0{random.randint(100,199)}",
                    "height_cm": random.randint(158, 192),
                    "weight_kg": random.randint(55, 95),
                    "fitness_level": random.choice(["BEGINNER", "INTERMEDIATE", "ADVANCED"]),
                    "fitness_goal": random.choice(["Lose fat", "Build muscle", "General fitness", "Marathon training"]),
                },
            )
            prof.raise_for_status()
            photo = self.upload(token, "/members/me/photo", make_image(name.split()[0], i + 10))
            out.append({"email": email, "token": token, "id": photo["id"], "name": name})
            print(f"[seed] member {name} -> {photo['id']}")
        return out

    def exercises(self, admin: str) -> list[dict]:
        roster = [
            ("Barbell Bench Press", "Chest", "Barbell, Bench", "INTERMEDIATE", "Lie flat, lower bar to chest, press up."),
            ("Back Squat", "Legs", "Barbell, Rack", "INTERMEDIATE", "Bar on traps, squat to parallel, drive up."),
            ("Deadlift", "Back", "Barbell", "ADVANCED", "Hinge at hips, keep bar close, stand tall."),
            ("Pull-up", "Back", "Pull-up Bar", "INTERMEDIATE", "Dead hang, pull chin over bar."),
            ("Overhead Press", "Shoulders", "Barbell", "INTERMEDIATE", "Press bar overhead from shoulder height."),
            ("Dumbbell Bicep Curl", "Arms", "Dumbbells", "BEGINNER", "Curl dumbbells to shoulder, control the descent."),
            ("Plank", "Core", "Bodyweight", "BEGINNER", "Hold a straight line from shoulders to heels."),
            ("Walking Lunges", "Legs", "Dumbbells", "BEGINNER", "Step forward into a lunge, alternate legs."),
            ("Lat Pulldown", "Back", "Cable Machine", "BEGINNER", "Pull bar to upper chest, control the return."),
            ("Tricep Dip", "Arms", "Dip Bars", "INTERMEDIATE", "Lower body until elbows at 90°, press up."),
            ("Leg Press", "Legs", "Leg Press Machine", "BEGINNER", "Press platform away, don't lock out knees."),
            ("Russian Twist", "Core", "Medicine Ball", "BEGINNER", "Rotate torso side to side, feet off floor."),
        ]
        out = []
        for i, (name, mg, equip, diff, instr) in enumerate(roster):
            r = self.c.post(
                "/exercises", headers=self.auth(admin),
                json={"name": name, "description": f"{name} — targets the {mg.lower()}.", "muscle_group": mg,
                      "equipment": equip, "difficulty": diff, "instructions": instr},
            )
            r.raise_for_status()
            ex = r.json()
            self.upload(admin, f"/exercises/{ex['id']}/media", make_image(name.split()[0], i + 20))
            out.append(ex)
        print(f"[seed] {len(out)} exercises")
        return out

    def workouts(self, trainer: dict, member: dict, exercises: list[dict]) -> None:
        picks = random.sample(exercises, 4)
        body = {
            "member_id": member["id"], "name": f"{member['name'].split()[0]}'s Foundations Program",
            "description": "A 3-day full body split.", "start_date": None, "end_date": None,
            "days": [
                {"day_number": 1, "name": "Day 1 — Push", "exercises": [
                    {"exercise_id": picks[0]["id"], "sets": 4, "reps": 8, "target_weight_kg": 40.0, "rest_seconds": 90, "order_index": 0},
                    {"exercise_id": picks[1]["id"], "sets": 3, "reps": 10, "target_weight_kg": 20.0, "rest_seconds": 60, "order_index": 1},
                ]},
                {"day_number": 2, "name": "Day 2 — Pull", "exercises": [
                    {"exercise_id": picks[2]["id"], "sets": 4, "reps": 6, "target_weight_kg": 60.0, "rest_seconds": 120, "order_index": 0},
                ]},
                {"day_number": 3, "name": "Day 3 — Legs", "exercises": [
                    {"exercise_id": picks[3]["id"], "sets": 4, "reps": 10, "target_weight_kg": 50.0, "rest_seconds": 90, "order_index": 0},
                ]},
            ],
        }
        r = self.c.post("/workouts/programs", headers=self.auth(trainer["token"]), json=body)
        r.raise_for_status()
        program = r.json()
        day0 = program["days"][0]
        sess = self.c.post(
            "/workouts/sessions", headers=self.auth(member["token"]),
            json={"workout_day_id": day0["id"], "scheduled_date": str(datetime.now(UTC).date())},
        )
        sess.raise_for_status()
        session = sess.json()
        set_logs = [
            {"workout_exercise_id": we["id"], "set_number": n, "reps_done": we["reps"], "weight_used_kg": we["target_weight_kg"], "completed": True}
            for we in day0["exercises"] for n in range(1, we["sets"] + 1)
        ]
        self.c.post(
            f"/workouts/sessions/{session['id']}/complete", headers=self.auth(member["token"]),
            json={"set_logs": set_logs, "notes": "Felt strong today."},
        ).raise_for_status()
        print(f"[seed] workout program + completed session for {member['name']}")

    def classes(self, admin: str, trainers: list[dict]) -> list[dict]:
        now = datetime.now(UTC)
        roster = [
            ("Morning Yoga", "Gentle flow to start the day.", trainers[1]["id"], 20, "Studio A", 1, 7, 8),
            ("HIIT Blast", "45 minutes of high-intensity intervals.", trainers[2]["id"], 15, "Main Floor", 2, 18, 19),
            ("Strength Fundamentals", "Barbell technique for beginners.", trainers[0]["id"], 10, "Main Floor", 3, 17, 18),
            ("Spin Class", "45-minute indoor cycling session.", trainers[2]["id"], 18, "Studio B", 5, 9, 10),
        ]
        out = []
        for name, desc, trainer_id, cap, loc, days_ahead, start_h, end_h in roster:
            start = (now + timedelta(days=days_ahead)).replace(hour=start_h, minute=0, second=0, microsecond=0)
            end = start.replace(hour=end_h)
            r = self.c.post(
                "/classes", headers=self.auth(admin),
                json={"name": name, "description": desc, "trainer_id": trainer_id, "capacity": cap,
                      "location": loc, "start_time": start.isoformat(), "end_time": end.isoformat()},
            )
            r.raise_for_status()
            out.append(r.json())
        print(f"[seed] {len(out)} classes")
        return out

    def bookings(self, members: list[dict], classes: list[dict]) -> None:
        for member in members[:4]:
            for cls in random.sample(classes, 2):
                r = self.c.post(f"/classes/{cls['id']}/book", headers=self.auth(member["token"]))
                if r.status_code == 201:
                    print(f"[seed] {member['name']} booked {cls['name']}")

    def store(self, admin: str) -> tuple[list[dict], list[dict]]:
        cats = {}
        for name in ["Supplements", "Apparel", "Equipment", "Accessories"]:
            r = self.c.post("/store/categories", headers=self.auth(admin), json={"name": name, "description": f"{name} for members"})
            r.raise_for_status()
            cats[name] = r.json()["id"]
        roster = [
            ("Whey Protein 2lb", "Supplements", "24.99", "WP-2LB", 40),
            ("Creatine Monohydrate 300g", "Supplements", "14.99", "CR-300", 60),
            ("BCAA Powder", "Supplements", "19.99", "BCAA-01", 35),
            ("Iron Forge Gym T-Shirt", "Apparel", "22.00", "TS-BLK", 50),
            ("Compression Leggings", "Apparel", "34.00", "LG-001", 25),
            ("Resistance Bands Set", "Equipment", "18.50", "RB-SET", 30),
            ("Yoga Mat", "Equipment", "27.00", "YM-01", 20),
            ("Shaker Bottle 700ml", "Accessories", "9.99", "SB-700", 80),
            ("Lifting Gloves", "Accessories", "16.00", "LG-GLV", 45),
            ("Foam Roller", "Equipment", "21.00", "FR-01", 15),
        ]
        products = []
        for i, (name, cat, price, sku, stock) in enumerate(roster):
            r = self.c.post(
                "/store/products", headers=self.auth(admin),
                json={"category_id": cats[cat], "name": name, "description": f"{name} — available at the front desk or in-app.",
                      "price": price, "sku": sku, "stock_quantity": stock},
            )
            r.raise_for_status()
            product = r.json()
            self.upload(admin, f"/store/products/{product['id']}/images", make_image(name.split()[0], i + 40))
            products.append(product)
        promo = self.c.post(
            "/promotions", headers=self.auth(admin),
            json={"name": "Back to Fitness", "description": "15% off all supplements this month.",
                  "discount_type": "PERCENTAGE", "discount_value": "15",
                  "start_date": datetime.now(UTC).isoformat(),
                  "end_date": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
                  "category_ids": [cats["Supplements"]]},
        )
        promo.raise_for_status()
        print(f"[seed] {len(products)} products, 1 promotion")
        return list(cats.values()), products

    def checkout(self, member: dict, products: list[dict]) -> None:
        for p in random.sample(products, 2):
            self.c.post(
                "/store/cart/items", headers=self.auth(member["token"]),
                json={"product_id": p["id"], "quantity": random.randint(1, 2)},
            ).raise_for_status()
        r = self.c.post(
            "/store/checkout", headers=self.auth(member["token"]),
            json={"delivery_address": "482 Foundry Street, Springvale", "phone": "+1 555-0199", "notes": "Leave at front desk"},
        )
        r.raise_for_status()
        print(f"[seed] order placed for {member['name']}: {r.json()['id']}")

    def progress_and_logs(self, member: dict, exercises: list[dict]) -> None:
        self.c.post(
            "/progress/measurements", headers=self.auth(member["token"]),
            json={"recorded_at": datetime.now(UTC).isoformat(), "weight_kg": 78.5, "body_fat_pct": 18.2,
                  "chest_cm": 102, "waist_cm": 84, "notes": "Starting measurements"},
        ).raise_for_status()
        self.upload(member["token"], "/progress/photos", make_image("Progress", 50))
        self.c.post(
            "/progress/records", headers=self.auth(member["token"]),
            json={"exercise_id": exercises[0]["id"], "value": 100, "unit": "kg", "achieved_at": str(datetime.now(UTC).date())},
        ).raise_for_status()
        self.c.post("/water/entries", headers=self.auth(member["token"]), json={"amount_ml": 500}).raise_for_status()
        self.c.post("/water/entries", headers=self.auth(member["token"]), json={"amount_ml": 750}).raise_for_status()
        self.c.post(
            "/nutrition/meals", headers=self.auth(member["token"]),
            json={"name": "Grilled chicken & rice", "meal_type": "LUNCH", "calories": 650, "protein_g": 55, "carbs_g": 70, "fat_g": 12},
        ).raise_for_status()
        print(f"[seed] progress/water/nutrition logged for {member['name']}")

    def contact_and_feedback(self, member: dict) -> None:
        self.c.post(
            "/contact",
            json={"name": "Jordan Ellis", "email": "jordan.ellis@example.com", "phone": "+1 555-0177",
                  "subject": "Question about day passes", "message": "Do you offer single-day passes for visitors?"},
        ).raise_for_status()
        self.c.post(
            "/feedback", headers=self.auth(member["token"]),
            json={"rating": 5, "comment": "Great equipment and friendly trainers!"},
        ).raise_for_status()
        print("[seed] contact + feedback submitted")


def main() -> None:
    print(f"[seed] target: {BASE_URL}")
    reset_admin_password()
    s = Seeder()
    admin = s.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    print(f"[seed] logged in as admin ({ADMIN_EMAIL} / {ADMIN_PASSWORD})")

    s.gym_info(admin)
    trainers = s.trainers(admin)
    plans = s.plans(admin)

    names = ["Sara Ahmed", "James Cooper", "Lina Fischer", "Omar Haddad", "Zoe Turner", "David Kim"]
    members = s.members(names[:3])
    print("[seed] sleeping 65s to respect the 3/min register rate limit...")
    time.sleep(65)
    members += s.members(names[3:])

    for member, plan in zip(members, [plans[0], plans[1], plans[0], plans[2]]):
        r = s.c.post("/memberships/subscribe", headers=s.auth(member["token"]), json={"plan_id": plan["id"]})
        r.raise_for_status()
        sub = r.json()
        if random.random() < 0.6:
            s.c.post(f"/memberships/{sub['id']}/confirm-payment", headers=s.auth(admin), json={"notes": "Paid cash at front desk"}).raise_for_status()

    for member, trainer in [(members[0], trainers[0]), (members[1], trainers[1])]:
        s.c.post("/members/assign-trainer", headers=s.auth(admin), json={"member_id": member["id"], "trainer_id": trainer["id"]}).raise_for_status()

    exercises = s.exercises(admin)
    s.workouts(trainers[0], members[0], exercises)
    s.workouts(trainers[1], members[1], exercises)

    classes = s.classes(admin, trainers)
    s.bookings(members, classes)

    _, products = s.store(admin)
    s.checkout(members[2], products)
    s.checkout(members[3], products)

    s.progress_and_logs(members[0], exercises)
    s.progress_and_logs(members[1], exercises)

    s.contact_and_feedback(members[4])

    print("\n[seed] done.")
    print(f"[seed] admin login -> {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"[seed] all demo trainers/members share password -> {DEMO_PASSWORD}")
    for m in members:
        print(f"[seed]   member: {m['email']}")
    for t in trainers:
        print(f"[seed]   trainer: {t['email']}")


if __name__ == "__main__":
    main()
