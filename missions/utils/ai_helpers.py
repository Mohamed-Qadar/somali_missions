from django.utils.translation import gettext_lazy as _


def classify_complaint_ai(subject, message, category=None):
    """
    Simulates AI classification of a complaint based on keyword analysis.
    Detects urgency/priority, suggests a department, and suggests a category.
    """
    text = f"{subject} {message}".lower()

    critical_keywords = [
        "hospital", "medical", "arrest", "jail", "police", "detain", "kidnap",
        "abuse", "assault", "violence", "human trafficking", "stranded", "war",
        "conflict", "deport", "child protection", "prison", "emergency", "beaten",
        "xarig", "xabsi", "isbitaal", "dagaal", "dhaawac", "kufsi", "tahriib",
        "dhibaato", "gacan ka hadal", "musiibo", "deportation",
    ]

    high_keywords = [
        "bribe", "corruption", "stolen", "lost passport", "refusal", "money",
        "demand", "payment", "stole", "lost document", "passport delay",
        "laaluush", "xatooyo", "lumay", "diidmo", "lacag", "baasaboor", "dhaqan xumo",
    ]

    medium_keywords = [
        "delay", "appointment", "wait", "slow", "queue", "system down",
        "daahitaan", "balan", "sugi", "nidaamka",
    ]

    priority = "LOW"
    if any(k in text for k in critical_keywords):
        priority = "CRITICAL"
    elif any(k in text for k in high_keywords):
        priority = "HIGH"
    elif any(k in text for k in medium_keywords):
        priority = "MEDIUM"

    suggested_category = "OTHER"
    if "emergency" in text or "hospital" in text or "arrest" in text or "xarig" in text:
        suggested_category = "EMERGENCY"
    elif "corruption" in text or "bribe" in text or "laaluush" in text or "money" in text:
        suggested_category = "CORRUPTION"
    elif "passport" in text or "baasaboor" in text or "baasabor" in text:
        suggested_category = "PASSPORT"
    elif "visa" in text or "fiiso" in text:
        suggested_category = "VISA"
    elif "appointment" in text or "balan" in text or "ballan" in text:
        suggested_category = "APPOINTMENT"
    elif "rude" in text or "misconduct" in text or "staff" in text or "dhaqan" in text:
        suggested_category = "STAFF"
    elif "lost" in text or "lumay" in text:
        suggested_category = "LOST_DOCS"
    elif "auth" in text or "legal" in text or "verify" in text or "shahaado" in text:
        suggested_category = "AUTHENTICATION"
    elif "consular" in text or "service" in text:
        suggested_category = "CONSULAR"

    department = "Consular Services Department"
    if priority == "CRITICAL":
        department = "Emergency & Citizen Protection Division"
    elif suggested_category == "CORRUPTION":
        department = "Internal Audit & Anti-Corruption Bureau"
    elif suggested_category in ["PASSPORT", "VISA", "AUTHENTICATION"]:
        department = "Passport & Document Processing Division"
    elif suggested_category in ["STAFF", "OTHER"]:
        department = "Diplomatic Relations & Oversight Division"

    return {
        "priority": priority,
        "suggested_category": suggested_category,
        "department": department,
    }


def translate_text_ai(text, from_lang, to_lang):
    """
    Simulates AI translation between English and Somali.
    Provides a readable translation or mock fallback translation.
    """
    if not text:
        return ""

    translations = {
        "so": {
            "en": {
                "baasaboor": "passport",
                "lumay": "lost",
                "xarig": "arrest",
                "laaluush": "bribe",
                "isbitaal": "hospital",
                "dhibaato": "problem",
                "fadlan": "please",
                "caawi": "help",
                "dhakhso": "quickly",
                "safiirka": "ambassador",
                "safaarad": "embassy",
                "safaaradda": "embassy",
                "qunsuliyada": "consulate",
                "qunsuliyadda": "consulate",
            },
        },
        "en": {
            "so": {
                "passport": "baasaboor",
                "lost": "lumay",
                "arrest": "xarig",
                "bribe": "laaluush",
                "hospital": "isbitaal",
                "problem": "dhibaato",
                "please": "fadlan",
                "help": "caawi",
                "quickly": "dhakhso",
                "ambassador": "safiirka",
                "embassy": "safaarad",
                "consulate": "qunsuliyad",
            },
        },
    }

    clean_from = from_lang.lower()[:2]
    clean_to = to_lang.lower()[:2]

    if clean_from == clean_to:
        return text

    dict_trans = translations.get(clean_from, {}).get(clean_to, {})
    translated_words = []
    for word in text.split():
        clean_word = "".join(c for c in word if c.isalnum()).lower()
        translated_words.append(dict_trans.get(clean_word, word))

    prefix = {
        "en": "[AI Translated to EN]: ",
        "so": "[AI loo turjumay SO]: ",
    }
    return f"{prefix.get(clean_to, '')}{' '.join(translated_words)}"
