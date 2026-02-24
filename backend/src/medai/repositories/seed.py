"""Seed data — realistic demo patients and comprehensive timeline events.

Loaded on startup so the API has rich data for demos and testing.
Each patient has a multi-visit longitudinal story that the agentic
pipeline can reason about when history_search is invoked.
"""

from __future__ import annotations

from datetime import date, datetime

from medai.domain.entities import (
    Gender,
    Patient,
    TimelineEvent,
    TimelineEventType,
    User,
    UserRole,
)


def create_admin_user() -> User:
    """Create default admin user (password: admin123)."""
    from medai.api.auth import hash_password

    return User(
        id="USR-ADMIN001",
        email="admin@medai.com",
        hashed_password=hash_password("admin123"),
        name="System Administrator",
        role=UserRole.ADMIN,
        is_active=True,
    )


def create_doctor_user() -> User:
    """Create default doctor user (password: doctor123)."""
    from medai.api.auth import hash_password

    return User(
        id="USR-DOCTOR01",
        email="doctor@medai.com",
        hashed_password=hash_password("doctor123"),
        name="Dr. Demo Physician",
        role=UserRole.DOCTOR,
        is_active=True,
    )


def create_seed_patients() -> list[Patient]:
    """Create demo patients with rich backstories for demo.

    Each patient represents a different clinical scenario:
    1. Maria Ivanova — respiratory case (pneumonia progression)
    2. Oleksandr Petrenko — chronic disease management (DM + renal)
    3. Natalia Kovalenko — dermatology + oncology screening
    """
    return [
        Patient(
            id="PT-DEMO0001",
            name="Maria Ivanova",
            date_of_birth=date(1962, 3, 15),
            gender=Gender.FEMALE,
            medical_record_number="MRN-2024-001",
        ),
        Patient(
            id="PT-DEMO0002",
            name="Oleksandr Petrenko",
            date_of_birth=date(1972, 11, 22),
            gender=Gender.MALE,
            medical_record_number="MRN-2024-002",
        ),
        Patient(
            id="PT-DEMO0003",
            name="Natalia Kovalenko",
            date_of_birth=date(1995, 7, 8),
            gender=Gender.FEMALE,
            medical_record_number="MRN-2024-003",
        ),
        Patient(
            id="PT-DEMO0004",
            name="Dmytro Shevchenko",
            date_of_birth=date(1958, 4, 29),
            gender=Gender.MALE,
            medical_record_number="MRN-2024-004",
        ),
    ]


def create_seed_timeline_events() -> list[TimelineEvent]:
    """Create comprehensive multi-visit timelines linked to seed patients.

    These timelines tell a clinical story that the agentic pipeline
    can reference via history_search during case analysis.
    """
    return [
        # ══════════════════════════════════════════════════
        #  Maria Ivanova (PT-DEMO0001) — Respiratory Case
        #  Story: Smoker → recurrent pneumonia → COPD diagnosis
        # ══════════════════════════════════════════════════

        # Visit 1: Initial presentation (6 months ago)
        TimelineEvent(
            id="TL-SEED0001",
            patient_id="PT-DEMO0001",
            date=datetime(2025, 8, 12, 9, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "Initial consultation — 62F, 35-pack-year smoker. Progressive dyspnea on exertion "
                "for 2 months, productive cough with white sputum. No hemoptysis. "
                "PMH: Hypertension (Amlodipine 5mg), GERD. Auscultation: diminished breath sounds bilaterally."
            ),
            source_type="encounter",
            metadata={"chief_complaint": "progressive dyspnea", "provider": "Dr. Bondarenko"},
        ),
        TimelineEvent(
            id="TL-SEED0002",
            patient_id="PT-DEMO0001",
            date=datetime(2025, 8, 12, 10, 30),
            event_type=TimelineEventType.LAB,
            summary=(
                "CBC: WBC 8.1×10⁹/L (normal), Hgb 13.2 g/dL, CRP 6 mg/L (mildly elevated). "
                "BMP: Na 141, K 4.2, Cr 0.9 mg/dL, BUN 16. SpO₂ 95% on room air."
            ),
            source_type="lab",
            metadata={"wbc": 8.1, "crp": 6.0, "spo2": 95, "creatinine": 0.9},
        ),
        TimelineEvent(
            id="TL-SEED0003",
            patient_id="PT-DEMO0001",
            date=datetime(2025, 8, 13, 14, 0),
            event_type=TimelineEventType.IMAGING,
            summary=(
                "Chest X-ray PA view: Hyperinflated lungs, flattened diaphragms consistent with emphysema. "
                "No focal consolidation, no pleural effusion. Cardiothoracic ratio 0.48 (normal). "
                "Impression: Findings consistent with COPD/emphysema."
            ),
            source_type="imaging",
            metadata={"modality": "xray", "body_region": "chest", "impression": "COPD/emphysema"},
        ),
        TimelineEvent(
            id="TL-SEED0004",
            patient_id="PT-DEMO0001",
            date=datetime(2025, 8, 14, 11, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "Pulmonary function test (PFT): FEV1 62% predicted, FEV1/FVC 0.63. "
                "Post-bronchodilator FEV1 improvement 8% (not reversible). "
                "Diagnosis: COPD GOLD Stage II (moderate). "
                "Started on Tiotropium 18mcg QD + Salbutamol PRN. Smoking cessation counseling."
            ),
            source_type="encounter",
            metadata={"fev1_percent": 62, "fev1_fvc": 0.63, "gold_stage": "II"},
        ),

        # Visit 2: 3 months later — stable COPD follow-up
        TimelineEvent(
            id="TL-SEED0005",
            patient_id="PT-DEMO0001",
            date=datetime(2025, 11, 10, 9, 30),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "3-month COPD follow-up. Patient reports improved exercise tolerance, "
                "still smoking 10 cigarettes/day (down from 20). Occasional morning cough. "
                "SpO₂ 96%. Auscultation: scattered expiratory wheezes bilaterally. "
                "Continue current regimen. Repeat PFT in 3 months."
            ),
            source_type="encounter",
            metadata={"chief_complaint": "COPD follow-up", "spo2": 96},
        ),
        TimelineEvent(
            id="TL-SEED0006",
            patient_id="PT-DEMO0001",
            date=datetime(2025, 11, 10, 10, 0),
            event_type=TimelineEventType.LAB,
            summary="CRP 4 mg/L (normal). HbA1c 5.8% (pre-diabetic range). Lipid panel: TC 220, LDL 145.",
            source_type="lab",
            metadata={"crp": 4.0, "hba1c": 5.8, "ldl": 145},
        ),

        # Visit 3: Current (acute presentation) — pneumonia + COPD exacerbation
        TimelineEvent(
            id="TL-SEED0007",
            patient_id="PT-DEMO0001",
            date=datetime(2026, 2, 5, 16, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "Acute presentation — 3-week progressive dyspnea, productive cough with "
                "yellowish-green sputum, low-grade fever (37.8°C). Worse in past 3 days. "
                "Cannot walk >50m without stopping. Night sweats. Weight loss 3kg in 2 weeks. "
                "Exam: tachypneic RR 24, decreased breath sounds RLL with dullness to percussion, "
                "scattered crackles. SpO₂ 91% on room air."
            ),
            source_type="encounter",
            metadata={
                "chief_complaint": "acute dyspnea and fever",
                "spo2": 91,
                "temperature": 37.8,
                "rr": 24,
            },
        ),
        TimelineEvent(
            id="TL-SEED0008",
            patient_id="PT-DEMO0001",
            date=datetime(2026, 2, 5, 17, 0),
            event_type=TimelineEventType.LAB,
            summary=(
                "STAT labs: WBC 14.8×10⁹/L (H), Neutrophils 82%, CRP 92 mg/L (H), "
                "Procalcitonin 1.2 ng/mL (H — suggests bacterial). ABG: pH 7.38, pCO₂ 46, pO₂ 62. "
                "D-dimer 0.4 (normal). Sputum sent for culture and sensitivity."
            ),
            source_type="lab",
            metadata={"wbc": 14.8, "crp": 92, "procalcitonin": 1.2, "pco2": 46, "po2": 62},
        ),
        TimelineEvent(
            id="TL-SEED0009",
            patient_id="PT-DEMO0001",
            date=datetime(2026, 2, 6, 8, 0),
            event_type=TimelineEventType.IMAGING,
            summary=(
                "Chest X-ray (current): Right lower lobe consolidation with air bronchograms. "
                "Small right-sided pleural effusion (new). Left lung hyperinflated, consistent with "
                "known emphysema. Cardiothoracic ratio 0.50 (borderline). "
                "Comparison with Aug 2025: new RLL consolidation and effusion."
            ),
            source_type="imaging",
            metadata={
                "modality": "xray",
                "body_region": "chest",
                "impression": "RLL pneumonia with small effusion, known COPD",
            },
        ),

        # ══════════════════════════════════════════════════
        #  Oleksandr Petrenko (PT-DEMO0002) — Diabetes + Renal
        #  Story: Well-controlled DM → worsening → early nephropathy
        # ══════════════════════════════════════════════════

        # Visit 1: Baseline (8 months ago)
        TimelineEvent(
            id="TL-SEED0010",
            patient_id="PT-DEMO0002",
            date=datetime(2025, 5, 10, 8, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "Annual diabetes review — 52M, T2DM × 10 years. Currently on Metformin 1000mg BID "
                "and Lisinopril 20mg daily for HTN. Asymptomatic, good adherence. "
                "BMI 31.2. BP 138/82. Feet exam: intact sensation, no ulcers."
            ),
            source_type="encounter",
            metadata={"chief_complaint": "annual DM review", "bmi": 31.2, "bp": "138/82"},
        ),
        TimelineEvent(
            id="TL-SEED0011",
            patient_id="PT-DEMO0002",
            date=datetime(2025, 5, 10, 8, 30),
            event_type=TimelineEventType.LAB,
            summary=(
                "HbA1c 6.8% (at target). Fasting glucose 128 mg/dL. "
                "Creatinine 1.0 mg/dL, eGFR 92 mL/min. Urine ACR 22 mg/g (normal <30). "
                "Lipids: TC 195, LDL 115, HDL 42, TG 180."
            ),
            source_type="lab",
            metadata={"hba1c": 6.8, "creatinine": 1.0, "egfr": 92, "urine_acr": 22},
        ),
        TimelineEvent(
            id="TL-SEED0012",
            patient_id="PT-DEMO0002",
            date=datetime(2025, 6, 15, 11, 0),
            event_type=TimelineEventType.IMAGING,
            summary="Fundus photography: No diabetic retinopathy detected. Optic disc normal. No macular edema.",
            source_type="imaging",
            metadata={"modality": "fundus", "retinopathy_grade": "none"},
        ),

        # Visit 2: Worsening glycemic control (3 months ago)
        TimelineEvent(
            id="TL-SEED0013",
            patient_id="PT-DEMO0002",
            date=datetime(2025, 11, 18, 9, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "Unscheduled visit — increased thirst and polyuria for 4 weeks. "
                "Reports high stress at work, irregular meals, less physical activity. "
                "Weight increased 4kg since last visit. BP 145/88. Fasting glucose at point-of-care: 210 mg/dL."
            ),
            source_type="encounter",
            metadata={"chief_complaint": "polyuria and polydipsia", "fasting_glucose_poc": 210},
        ),
        TimelineEvent(
            id="TL-SEED0014",
            patient_id="PT-DEMO0002",
            date=datetime(2025, 11, 18, 9, 30),
            event_type=TimelineEventType.LAB,
            summary=(
                "HbA1c 8.2% (↑ from 6.8%). Fasting glucose 195 mg/dL. "
                "Creatinine 1.3 mg/dL (↑), eGFR 68 mL/min (↓). Urine ACR 85 mg/g (↑, microalbuminuria). "
                "Potassium 5.0 mEq/L (upper normal). "
                "Assessment: Worsening glycemic control with early diabetic nephropathy (A2)."
            ),
            source_type="lab",
            metadata={"hba1c": 8.2, "creatinine": 1.3, "egfr": 68, "urine_acr": 85},
        ),
        TimelineEvent(
            id="TL-SEED0015",
            patient_id="PT-DEMO0002",
            date=datetime(2025, 11, 18, 10, 0),
            event_type=TimelineEventType.NOTE,
            summary=(
                "Plan: Add Empagliflozin 10mg daily (dual benefit — glycemic + renal protection). "
                "Increase Lisinopril to 40mg. Dietitian referral. Repeat labs in 3 months. "
                "If HbA1c still >7.5%, consider GLP-1 agonist or insulin."
            ),
            source_type="note",
            metadata={"medications_changed": ["empagliflozin_10mg_added", "lisinopril_increased_40mg"]},
        ),

        # Visit 3: Current follow-up — checking treatment response
        TimelineEvent(
            id="TL-SEED0016",
            patient_id="PT-DEMO0002",
            date=datetime(2026, 2, 7, 8, 30),
            event_type=TimelineEventType.LAB,
            summary=(
                "3-month follow-up labs: HbA1c 7.4% (↓ from 8.2%, improving). "
                "Fasting glucose 155 mg/dL. Creatinine 1.2 mg/dL (stable). eGFR 72 mL/min (improved). "
                "Urine ACR 52 mg/g (↓ from 85, responding to SGLT2i + ACEi). "
                "K+ 4.6 mEq/L. LDL 108."
            ),
            source_type="lab",
            metadata={"hba1c": 7.4, "creatinine": 1.2, "egfr": 72, "urine_acr": 52},
        ),

        # ══════════════════════════════════════════════════
        #  Natalia Kovalenko (PT-DEMO0003) — Dermatology
        #  Story: Skin lesion → biopsy → melanoma staging
        # ══════════════════════════════════════════════════

        # Visit 1: Initial concern
        TimelineEvent(
            id="TL-SEED0017",
            patient_id="PT-DEMO0003",
            date=datetime(2025, 10, 1, 16, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "30F, no significant PMH. Noticed pigmented lesion on left forearm "
                "growing and changing color over 3 months. Family history: mother had melanoma at 55. "
                "Exam: 9mm asymmetric pigmented lesion with irregular borders, color variegation (brown/black). "
                "ABCDE criteria: A+, B+, C+, D+ (>6mm), E+ (evolving). Dermoscopy performed."
            ),
            source_type="encounter",
            metadata={"chief_complaint": "growing skin lesion", "lesion_size_mm": 9},
        ),
        TimelineEvent(
            id="TL-SEED0018",
            patient_id="PT-DEMO0003",
            date=datetime(2025, 10, 1, 16, 30),
            event_type=TimelineEventType.IMAGING,
            summary=(
                "Dermoscopic imaging: Asymmetric pigment network, blue-white veil present, "
                "irregular dots/globules, regression structures. Dermoscopy score (7-point checklist): 5 "
                "(high suspicion for melanoma). Recommended: excisional biopsy with 2mm margins."
            ),
            source_type="imaging",
            metadata={"modality": "dermatology", "dermoscopy_score": 5},
        ),

        # Visit 2: Biopsy results
        TimelineEvent(
            id="TL-SEED0019",
            patient_id="PT-DEMO0003",
            date=datetime(2025, 10, 15, 10, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "Biopsy results discussion. Pathology: Superficial spreading melanoma, "
                "Breslow thickness 0.8mm, Clark level III, no ulceration, mitotic rate <1/mm². "
                "Margins clear. Sentinel lymph node biopsy discussed — patient consents. "
                "Stage: pT1a (preliminary, pending SLNB)."
            ),
            source_type="encounter",
            metadata={"breslow_thickness_mm": 0.8, "clark_level": "III", "ulceration": False},
        ),
        TimelineEvent(
            id="TL-SEED0020",
            patient_id="PT-DEMO0003",
            date=datetime(2025, 10, 15, 10, 30),
            event_type=TimelineEventType.LAB,
            summary="Pre-surgical labs: CBC normal, CMP normal, LDH 180 U/L (normal). S100B 0.05 µg/L (normal).",
            source_type="lab",
            metadata={"ldh": 180, "s100b": 0.05},
        ),

        # Visit 3: Post-surgery follow-up
        TimelineEvent(
            id="TL-SEED0021",
            patient_id="PT-DEMO0003",
            date=datetime(2025, 11, 5, 14, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "Post wide local excision + SLNB results. SLNB: negative (0/2 nodes). "
                "Final staging: Stage IA (pT1a N0 M0). Excellent prognosis — "
                "10-year survival >95%. Plan: clinical surveillance every 3 months × 2 years, "
                "then every 6 months × 3 years. Full-body skin exams. Sun protection education."
            ),
            source_type="encounter",
            metadata={"stage": "IA", "slnb_result": "negative", "nodes_examined": 2},
        ),

        # Visit 4: Current — 3-month surveillance
        TimelineEvent(
            id="TL-SEED0022",
            patient_id="PT-DEMO0003",
            date=datetime(2026, 2, 4, 15, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "3-month melanoma surveillance. Surgical scar well-healed. "
                "Full skin exam: no suspicious lesions. Patient reports new 4mm mole on upper back, "
                "appears symmetric and uniform — clinically benign. Dermoscopy scheduled for documentation."
            ),
            source_type="encounter",
            metadata={"chief_complaint": "melanoma surveillance", "new_lesion": True},
        ),
        TimelineEvent(
            id="TL-SEED0023",
            patient_id="PT-DEMO0003",
            date=datetime(2026, 2, 4, 15, 30),
            event_type=TimelineEventType.IMAGING,
            summary=(
                "Dermoscopic image of new 4mm mole on upper back: symmetric pigment network, "
                "homogeneous brown coloration, regular dots. No blue-white veil, no regression. "
                "Assessment: benign-appearing compound nevus. Continue surveillance."
            ),
            source_type="imaging",
            metadata={"modality": "dermatology", "assessment": "benign compound nevus"},
        ),

        # ══════════════════════════════════════════════════
        #  Dmytro Shevchenko (PT-DEMO0004) — Cardiology
        #  Story: Chest pain → ACS workup → coronary artery disease
        # ══════════════════════════════════════════════════

        # Visit 1: Emergency presentation
        TimelineEvent(
            id="TL-SEED0024",
            patient_id="PT-DEMO0004",
            date=datetime(2025, 9, 20, 22, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "Emergency presentation — 67M, crushing substernal chest pain radiating to left arm "
                "for 45 minutes. Associated diaphoresis and nausea. PMH: HTN (Losartan 50mg), "
                "hyperlipidemia (Atorvastatin 20mg), ex-smoker (quit 5 years ago, 30-pack-year). "
                "FH: father MI at 58. Vitals: BP 165/95, HR 102, SpO₂ 97%. ECG: ST elevation V1-V4."
            ),
            source_type="encounter",
            metadata={
                "chief_complaint": "acute chest pain",
                "bp": "165/95",
                "hr": 102,
                "spo2": 97,
                "ecg": "ST elevation V1-V4",
            },
        ),
        TimelineEvent(
            id="TL-SEED0025",
            patient_id="PT-DEMO0004",
            date=datetime(2025, 9, 20, 22, 15),
            event_type=TimelineEventType.LAB,
            summary=(
                "STAT cardiac biomarkers: Troponin I 0.08 ng/mL (elevated, normal <0.04). "
                "CK-MB 12 U/L (elevated). BNP 280 pg/mL. CBC: WBC 11.2×10⁹/L. "
                "Creatinine 1.1 mg/dL. PT/INR 1.0. Lipid panel: TC 245, LDL 158, HDL 38, TG 210."
            ),
            source_type="lab",
            metadata={"troponin": 0.08, "ckmb": 12, "bnp": 280, "ldl": 158},
        ),
        TimelineEvent(
            id="TL-SEED0026",
            patient_id="PT-DEMO0004",
            date=datetime(2025, 9, 20, 22, 30),
            event_type=TimelineEventType.IMAGING,
            summary=(
                "Bedside echocardiogram: anterior wall hypokinesis, LVEF ~40% (reduced). "
                "No pericardial effusion. Mild mitral regurgitation. "
                "Assessment: consistent with acute anterior STEMI."
            ),
            source_type="imaging",
            metadata={"modality": "ultrasound", "lvef": 40, "wall_motion": "anterior hypokinesis"},
        ),

        # Visit 2: Post-PCI recovery
        TimelineEvent(
            id="TL-SEED0027",
            patient_id="PT-DEMO0004",
            date=datetime(2025, 9, 21, 6, 0),
            event_type=TimelineEventType.PROCEDURE,
            summary=(
                "Urgent coronary angiography + PCI: LAD 95% stenosis with thrombus — "
                "successful drug-eluting stent (DES) placement. RCA 40% stenosis (non-flow-limiting). "
                "Post-PCI TIMI 3 flow. Access: right radial. No complications."
            ),
            source_type="procedure",
            metadata={"stenosis_lad": 95, "stenosis_rca": 40, "stent": "DES", "timi_flow": 3},
        ),
        TimelineEvent(
            id="TL-SEED0028",
            patient_id="PT-DEMO0004",
            date=datetime(2025, 9, 22, 8, 0),
            event_type=TimelineEventType.LAB,
            summary=(
                "Post-PCI Day 1 labs: Peak Troponin I 8.2 ng/mL (confirming moderate-size MI). "
                "CK-MB peaked at 95 U/L. Creatinine stable 1.1 mg/dL. "
                "Hemoglobin 13.8 g/dL. Platelets 240×10⁹/L."
            ),
            source_type="lab",
            metadata={"troponin_peak": 8.2, "ckmb_peak": 95, "creatinine": 1.1},
        ),
        TimelineEvent(
            id="TL-SEED0029",
            patient_id="PT-DEMO0004",
            date=datetime(2025, 9, 23, 10, 0),
            event_type=TimelineEventType.NOTE,
            summary=(
                "Discharge plan: DAPT (Aspirin 81mg + Clopidogrel 75mg × 12 months), "
                "Atorvastatin increased to 80mg, Metoprolol 50mg BID, Ramipril 5mg daily. "
                "Cardiac rehab referral. Follow-up echo in 6 weeks. No driving × 4 weeks."
            ),
            source_type="note",
            metadata={
                "medications": [
                    "aspirin_81mg",
                    "clopidogrel_75mg",
                    "atorvastatin_80mg",
                    "metoprolol_50mg_bid",
                    "ramipril_5mg",
                ],
            },
        ),

        # Visit 3: 6-week follow-up
        TimelineEvent(
            id="TL-SEED0030",
            patient_id="PT-DEMO0004",
            date=datetime(2025, 11, 4, 9, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary=(
                "6-week post-STEMI follow-up. Chest pain-free. Completing cardiac rehab phase 1. "
                "Functional capacity improved — can walk 30 minutes without symptoms. BP 128/78, HR 62. "
                "Adherent to all medications. Mild fatigue attributed to beta-blocker."
            ),
            source_type="encounter",
            metadata={"chief_complaint": "post-STEMI follow-up", "bp": "128/78", "hr": 62},
        ),
        TimelineEvent(
            id="TL-SEED0031",
            patient_id="PT-DEMO0004",
            date=datetime(2025, 11, 4, 10, 0),
            event_type=TimelineEventType.IMAGING,
            summary=(
                "Follow-up echocardiogram: LVEF improved to 48% (from 40% at presentation). "
                "Anterior wall still mildly hypokinetic but improved. No LV thrombus. "
                "Mild mitral regurgitation (stable). Diastolic function grade I."
            ),
            source_type="imaging",
            metadata={"modality": "ultrasound", "lvef": 48, "improvement": True},
        ),
        TimelineEvent(
            id="TL-SEED0032",
            patient_id="PT-DEMO0004",
            date=datetime(2025, 11, 4, 10, 30),
            event_type=TimelineEventType.LAB,
            summary=(
                "Follow-up labs: LDL 72 mg/dL (at target on high-dose statin). "
                "HbA1c 5.6% (normal). Creatinine 1.0 mg/dL. BNP 85 pg/mL (improving). "
                "Liver enzymes normal (no statin toxicity)."
            ),
            source_type="lab",
            metadata={"ldl": 72, "hba1c": 5.6, "bnp": 85, "creatinine": 1.0},
        ),
    ]
