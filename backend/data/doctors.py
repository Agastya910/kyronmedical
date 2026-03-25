"""
Hard-coded doctors, specialties, and 60-day availability window.
Availability covers April 25 – June 24, 2026.
"""
from datetime import date, timedelta
import random

random.seed(42)  # reproducible for demos

START_DATE = date(2026, 4, 25)
END_DATE   = date(2026, 6, 24)

DOCTORS = [
    {
        "id": "dr_chen",
        "name": "Dr. Sarah Chen",
        "specialty": "Orthopedic Surgery",
        "specialty_description": (
            "Orthopedics — treats bones joints muscles ligaments tendons spine "
            "fractures arthritis back pain knee pain hip pain shoulder pain sports "
            "injuries ACL torn meniscus carpal tunnel musculoskeletal disorders"
        ),
        "bio": "Board-certified orthopedic surgeon with 15 years of experience in sports medicine and joint replacement.",
        "photo_placeholder": "SC",
    },
    {
        "id": "dr_webb",
        "name": "Dr. Marcus Webb",
        "specialty": "Cardiology",
        "specialty_description": (
            "Cardiology — treats heart cardiovascular chest pain palpitations high "
            "blood pressure hypertension heart disease arrhythmia irregular heartbeat "
            "shortness of breath coronary artery disease heart attack angina echocardiogram"
        ),
        "bio": "Interventional cardiologist specializing in preventive cardiology and heart failure management.",
        "photo_placeholder": "MW",
    },
    {
        "id": "dr_nair",
        "name": "Dr. Priya Nair",
        "specialty": "Dermatology",
        "specialty_description": (
            "Dermatology — treats skin hair nails rash acne eczema psoriasis moles "
            "warts hair loss alopecia nail disorders skin infections dermatitis "
            "rosacea melanoma suspicious lesion skin cancer screening itching hives"
        ),
        "bio": "Dermatologist and dermatopathologist with expertise in medical, surgical, and cosmetic dermatology.",
        "photo_placeholder": "PN",
    },
    {
        "id": "dr_rivera",
        "name": "Dr. James Rivera",
        "specialty": "Neurology",
        "specialty_description": (
            "Neurology — treats brain nervous system headaches migraines dizziness "
            "numbness tingling memory problems seizures nerve pain neuropathy multiple "
            "sclerosis Parkinson tremors stroke concussion vertigo tinnitus"
        ),
        "bio": "Neurologist specializing in headache disorders, epilepsy, and neurodegenerative diseases.",
        "photo_placeholder": "JR",
    },
]

TIMES = ["9:00 AM", "10:00 AM", "11:00 AM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM"]


def _generate_slots(doctor_id: str) -> list[dict]:
    slots = []
    current = START_DATE
    while current <= END_DATE:
        if current.weekday() < 5:  # Mon–Fri
            if random.random() > 0.20:  # 80% chance of having availability
                day_times = random.sample(TIMES, random.randint(3, 5))
                for t in sorted(day_times, key=lambda x: TIMES.index(x)):
                    slots.append({
                        "date": current.isoformat(),
                        "day_of_week": current.strftime("%A"),
                        "display_date": current.strftime("%B %d, %Y"),
                        "time": t,
                        "available": True,
                        "slot_id": f"{doctor_id}_{current.isoformat()}_{t.replace(':', '').replace(' ', '')}",
                    })
        current += timedelta(days=1)
    return slots


# Pre-generate all slots
AVAILABILITY: dict[str, list[dict]] = {
    doc["id"]: _generate_slots(doc["id"]) for doc in DOCTORS
}

# Build a lookup dict for quick doctor retrieval
DOCTORS_BY_ID: dict[str, dict] = {doc["id"]: doc for doc in DOCTORS}

PRACTICE_INFO = {
    "name": "Kyron Medical Group",
    "address": "1250 Medical Center Drive, Suite 400, Houston, TX 77030",
    "phone": "(713) 555-0192",
    "email": "info@kyronmedical.com",
    "hours": {
        "Monday–Friday": "8:00 AM – 6:00 PM",
        "Saturday": "9:00 AM – 1:00 PM",
        "Sunday": "Closed",
    },
    "emergency": "For medical emergencies, call 911 or go to your nearest emergency room.",
}
