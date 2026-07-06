# -*- coding: utf-8 -*-
"""Executive PowerPoint for the Somali MFA consular platform.
python-pptx, 16:9, official navy/white theme, screenshot-frame motif.
Only real, implemented features are described."""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from PIL import Image

ROOT = r"C:\Users\Moha-qadar\OneDrive\Desktop\somali_missions"
SHOTS = os.path.join(ROOT, "presentation", "screenshots")
COAT = os.path.join(ROOT, "missions", "static", "images", "somalia-coat-of-arms.png")
OUT = os.path.join(ROOT, "presentation", "Somali_MFA_Consular_Platform.pptx")

# ---- palette ----
NAVY      = RGBColor(0x14, 0x2A, 0x47)
NAVY_DEEP = RGBColor(0x0E, 0x1F, 0x38)
PRIMARY   = RGBColor(0x00, 0x77, 0xA3)
SKY       = RGBColor(0x4C, 0x93, 0xD6)
ICE       = RGBColor(0xCA, 0xDC, 0xFC)
LIGHT     = RGBColor(0xF3, 0xF6, 0xFB)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
INK       = RGBColor(0x1E, 0x29, 0x3B)
MUTED     = RGBColor(0x5A, 0x69, 0x7B)
BORDER    = RGBColor(0xD7, 0xE0, 0xEC)
GOLD      = RGBColor(0xB4, 0x8A, 0x2E)
DANGER    = RGBColor(0xC0, 0x2A, 0x2A)

HEAD = "Cambria"
BODY = "Calibri"

EMU_IN = 914400
SW, SH = 13.333, 7.5

prs = Presentation()
prs.slide_width = Inches(SW)
prs.slide_height = Inches(SH)
BLANK = prs.slide_layouts[6]


def slide(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    r.fill.solid(); r.fill.fore_color.rgb = bg
    r.line.fill.background()
    r.shadow.inherit = False
    s.shapes._spTree.remove(r._element)
    s.shapes._spTree.insert(2, r._element)
    return s


def _set_font(run, size, bold, color, font, italic=False):
    run.font.size = Pt(size); run.font.bold = bold
    run.font.color.rgb = color; run.font.name = font
    run.font.italic = italic


def text(s, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space_after=6, line_spacing=1.0):
    """runs: list of paragraphs; each paragraph is a list of (txt,size,bold,color,font[,italic])."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(space_after); p.space_before = Pt(0)
        p.line_spacing = line_spacing
        for rr in para:
            run = p.add_run(); run.text = rr[0]
            _set_font(run, rr[1], rr[2], rr[3], rr[4], rr[5] if len(rr) > 5 else False)
    return tb


def _shadow(shape, blur=0.09, dist=0.055, alpha=62000):
    sp = shape._element.spPr
    lst = sp.find(qn('a:effectLst'))
    if lst is None:
        lst = sp.makeelement(qn('a:effectLst'), {}); sp.append(lst)
    sh = lst.makeelement(qn('a:outerShdw'), {
        'blurRad': str(int(blur * EMU_IN)), 'dist': str(int(dist * EMU_IN)),
        'dir': '5400000', 'rotWithShape': '0'})
    clr = sh.makeelement(qn('a:srgbClr'), {'val': '0E2036'})
    a = clr.makeelement(qn('a:alpha'), {'val': str(alpha)}); clr.append(a)
    sh.append(clr); lst.append(sh)


def screenshot(s, path, x, y, box_w, box_h, frame=True):
    iw, ih = Image.open(path).size
    ar = iw / ih
    w, h = box_w, box_w / ar
    if h > box_h:
        h = box_h; w = box_h * ar
    px = x + (box_w - w) / 2; py = y + (box_h - h) / 2
    if frame:
        pad = 0.04
        fr = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                Inches(px - pad), Inches(py - pad),
                                Inches(w + 2 * pad), Inches(h + 2 * pad))
        fr.fill.solid(); fr.fill.fore_color.rgb = WHITE
        fr.line.color.rgb = BORDER; fr.line.width = Pt(1)
        try:
            fr.adjustments[0] = 0.03
        except Exception:
            pass
        _shadow(fr)
    pic = s.shapes.add_picture(path, Inches(px), Inches(py), Inches(w), Inches(h))
    pic.line.color.rgb = BORDER; pic.line.width = Pt(0.75)
    return px, py, w, h


def chip(s, x, y, d, fill, glyph, gcolor=WHITE, gsize=15):
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    c.fill.solid(); c.fill.fore_color.rgb = fill; c.line.fill.background()
    c.shadow.inherit = False
    tf = c.text_frame; tf.word_wrap = False
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = glyph
    _set_font(run, gsize, True, gcolor, BODY)
    return c


def bullets(s, x, y, w, items, size=15, color=INK, gap=0.06, dot=PRIMARY, line_spacing=1.02):
    cy = y
    for it in items:
        chip(s, x, cy + 0.045, 0.11, dot, "", gsize=1)
        tb = s.shapes.add_textbox(Inches(x + 0.28), Inches(cy - 0.04), Inches(w - 0.28), Inches(1.2))
        tf = tb.text_frame; tf.word_wrap = True
        tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
        p = tf.paragraphs[0]; p.line_spacing = line_spacing
        run = p.add_run(); run.text = it
        _set_font(run, size, False, color, BODY)
        # estimate line count for spacing
        approx_chars = int((w - 0.28) / (size * 0.0092))
        lines = max(1, -(-len(it) // max(1, approx_chars)))
        cy += 0.30 * lines + gap
    return cy


def kicker(s, x, y, txt, color=PRIMARY):
    text(s, x, y, 9, 0.3, [[(txt.upper(), 12.5, True, color, BODY)]])


def title(s, x, y, txt, color=NAVY, size=33, w=None):
    text(s, x, y, w or (SW - 2 * x), 1.2, [[(txt, size, True, color, HEAD)]], line_spacing=1.0)


def notes(s, txt):
    s.notes_slide.notes_text_frame.text = txt


def footer(s, num, dark=False):
    col = RGBColor(0x9F, 0xB2, 0xC8) if dark else MUTED
    text(s, 0.6, 7.06, 8, 0.3,
         [[("Somali MFA — Digital Consular Services Platform", 9, False, col, BODY)]])
    text(s, SW - 1.6, 7.06, 1.0, 0.3, [[(str(num), 9, True, col, BODY)]], align=PP_ALIGN.RIGHT)


def card(s, x, y, w, h, fill=WHITE, line=BORDER, shadow=True, radius=0.06):
    c = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    c.fill.solid(); c.fill.fore_color.rgb = fill
    if line is None:
        c.line.fill.background()
    else:
        c.line.color.rgb = line; c.line.width = Pt(1)
    c.shadow.inherit = False
    try:
        c.adjustments[0] = radius
    except Exception:
        pass
    if shadow:
        _shadow(c, blur=0.07, dist=0.04, alpha=45000)
    return c


# =================================================================== SLIDE 1 — COVER
s = slide(NAVY)
# subtle deep panel on right
band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(SW), Inches(SH))
band.fill.solid(); band.fill.fore_color.rgb = NAVY; band.line.fill.background(); band.shadow.inherit = False
s.shapes.add_picture(COAT, Inches(SW/2 - 0.9), Inches(0.95), height=Inches(1.8))
text(s, 1, 3.0, SW - 2, 0.4, [[("FEDERAL REPUBLIC OF SOMALIA  •  MINISTRY OF FOREIGN AFFAIRS", 13, True, ICE, BODY)]], align=PP_ALIGN.CENTER)
text(s, 1.2, 3.5, SW - 2.4, 1.7,
     [[("Somali Global Citizen Support", 40, True, WHITE, HEAD)],
      [("& Digital Consular Services Platform", 40, True, WHITE, HEAD)]],
     align=PP_ALIGN.CENTER, line_spacing=1.02)
text(s, 1, 5.55, SW - 2, 0.4, [[("Modernising consular services for Somali citizens worldwide", 16, False, ICE, BODY, True)]], align=PP_ALIGN.CENTER)
text(s, 1, 6.35, SW - 2, 0.7,
     [[("Presented to the Ministry of Foreign Affairs", 13.5, True, WHITE, BODY)],
      [("Federal Republic of Somalia", 12, False, RGBColor(0x9F,0xB2,0xC8), BODY)]],
     align=PP_ALIGN.CENTER, space_after=2)
notes(s, "Good morning/afternoon, Honourable Minister, Deputy Ministers, Directors General, Ambassadors and Consuls. "
         "Today I will present a digital platform built to modernise how the Ministry of Foreign Affairs serves Somali "
         "citizens abroad — from finding their nearest mission, to booking appointments, tracking complaints, and "
         "receiving emergency assistance. Every screen you will see is a working part of the system, not a mock-up. "
         "The goal is a more transparent, responsive, and citizen-centred consular service.")

# =================================================================== SLIDE 2 — CHALLENGE
s = slide(LIGHT)
kicker(s, 0.6, 0.55, "The Challenge")
title(s, 0.6, 0.92, "Serving citizens across the world is hard today")
text(s, 0.6, 1.72, SW - 1.2, 0.5, [[("Somali citizens abroad often face avoidable barriers when they need consular help the most.", 15, False, MUTED, BODY)]])
challenges = [
    ("Long-distance travel", "Citizens travel hundreds of kilometres to a mission without knowing hours, services, or requirements."),
    ("Appointment difficulties", "No simple way to see availability or reserve a time; queues and repeat visits are common."),
    ("Emergency assistance", "In a crisis — detention, lost passport, medical — there is no fast, structured channel to the mission."),
    ("Communication gaps", "Citizens cannot see the status of their request, and follow-up depends on phone calls and email."),
    ("Document processing", "Travelling without the right documents leads to rejected visits, extra cost, and delay."),
    ("Limited transparency", "Neither citizens nor the Ministry have a clear, shared view of service quality and response times."),
]
gx, gy, cw, ch, gapx, gapy = 0.6, 2.35, 3.95, 1.9, 0.22, 0.22
for i, (h, d) in enumerate(challenges):
    r, cc = divmod(i, 3)
    x = gx + cc * (cw + gapx); y = gy + r * (ch + gapy)
    card(s, x, y, cw, ch)
    chip(s, x + 0.28, y + 0.28, 0.42, RGBColor(0xE7,0xEF,0xF9), "!", PRIMARY, 17)
    text(s, x + 0.28, y + 0.82, cw - 0.56, 0.4, [[(h, 15, True, NAVY, BODY)]])
    text(s, x + 0.28, y + 1.18, cw - 0.56, 0.7, [[(d, 11, False, MUTED, BODY)]], line_spacing=1.02)
footer(s, 2)
notes(s, "Before showing the solution, it helps to name the problem. A Somali citizen in London, Nairobi or Istanbul who "
         "needs a passport renewed, a document authenticated, or urgent help in an emergency faces six recurring barriers: "
         "the distance to a mission, difficulty getting an appointment, no fast emergency channel, no visibility of their "
         "case, uncertainty about required documents, and — for the Ministry — limited transparency into service "
         "quality. These are exactly the gaps the platform is designed to close.")

# =================================================================== SLIDE 3 — VISION
s = slide(NAVY)
kicker(s, 0.6, 0.55, "Project Vision", ICE)
title(s, 0.6, 0.92, "A modern, transparent, citizen-centred consular service", WHITE)
pillars = [
    ("Modern", "Digital-first services citizens can reach from anywhere, on any device."),
    ("Transparent", "Open service statistics and case status that build public trust."),
    ("Citizen-centred", "Designed around real citizen journeys — in English and Somali."),
    ("Connected", "One national network linking every mission, the Ministry, and communities."),
]
px, py, cw, ch, gapx = 0.6, 2.15, 2.86, 2.15, 0.2
for i, (h, d) in enumerate(pillars):
    x = px + i * (cw + gapx)
    card(s, x, py, cw, ch, fill=RGBColor(0x1C,0x35,0x54), line=RGBColor(0x2C,0x48,0x6B), shadow=False)
    chip(s, x + 0.3, py + 0.3, 0.5, PRIMARY, str(i + 1), WHITE, 16)
    text(s, x + 0.3, py + 1.0, cw - 0.6, 0.4, [[(h, 17, True, WHITE, HEAD)]])
    text(s, x + 0.3, py + 1.42, cw - 0.6, 0.9, [[(d, 12, False, ICE, BODY)]], line_spacing=1.05)
# bilingual + mobile proof insets (kept clear of the footer)
screenshot(s, os.path.join(SHOTS, "19-language-switch.png"), 0.7, 4.55, 5.4, 2.1)
screenshot(s, os.path.join(SHOTS, "20-mobile-view.png"), 11.0, 4.5, 1.8, 2.15)
text(s, 6.5, 4.9, 4.2, 1.7,
     [[("Built in for every citizen", 14, True, WHITE, BODY)],
      [("Full English & Somali language support and a fully mobile-responsive interface — so the service works on a phone, in the citizen’s own language.", 12, False, ICE, BODY)]],
     line_spacing=1.08, space_after=6)
footer(s, 3, dark=True)
notes(s, "Our vision rests on four principles. Modern: services are digital-first and reachable from anywhere. "
         "Transparent: service statistics and case status are open, which builds public trust. Citizen-centred: the "
         "system is designed around real journeys and is fully bilingual — English and Somali. Connected: it is one "
         "national network linking every mission, the Ministry, and verified community organisations. As you can see at "
         "the bottom, the interface is fully translated into Somali and works on mobile phones, which is how most "
         "citizens abroad will access it.")

# =================================================================== SLIDE 4 — PLATFORM OVERVIEW
s = slide(LIGHT)
kicker(s, 0.6, 0.55, "Platform Overview")
title(s, 0.6, 0.92, "One platform, many services")
text(s, 0.6, 1.72, 5.5, 3.2, [[("A single, official gateway that brings the Ministry’s consular services together in one place.", 14.5, False, MUTED, BODY)]])
mods = [
    "Worldwide mission directory with map & search",
    "Appointment booking with required-document checklists",
    "Complaint submission and public case tracking",
    "Emergency assistance channel with priority handling",
    "Verified community organisations & consular events",
    "Ministry oversight, analytics and public transparency",
]
bullets(s, 0.6, 2.5, 5.6, mods, size=14.5)
screenshot(s, os.path.join(SHOTS, "01-home.png"), 6.35, 1.55, 6.4, 3.05)
screenshot(s, os.path.join(SHOTS, "02-directory.png"), 6.35, 4.35, 6.4, 2.55)
footer(s, 4)
notes(s, "This is the platform’s public home. It is a single official gateway that unifies the Ministry’s consular "
         "services: a worldwide mission directory with a live map and search; appointment booking with document "
         "checklists; complaint submission and public tracking; an emergency channel; verified community organisations "
         "and events; and Ministry oversight with public transparency. The lower image shows the interactive global "
         "directory — a citizen anywhere can find their nearest mission and its services in seconds.")

# ---------- generic screenshot content slide ----------
def content_slide(num, kick, ttl, desc, shot, blist, shot_side="right", second=None,
                  notes_txt=""):
    s = slide(LIGHT)
    kicker(s, 0.6, 0.55, kick)
    title(s, 0.6, 0.92, ttl)
    if shot_side == "right":
        tx = 0.6; txw = 5.5
        text(s, tx, 1.72, txw, 0.9, [[(desc, 14.5, False, MUTED, BODY)]], line_spacing=1.05)
        bullets(s, tx, 2.62, txw + 0.1, blist, size=14.5)
        if second:
            screenshot(s, shot, 6.4, 1.55, 6.35, 2.75)
            screenshot(s, second, 6.4, 4.45, 6.35, 2.5)
        else:
            screenshot(s, shot, 6.35, 1.75, 6.4, 4.9)
    else:  # shot on left
        if second:
            screenshot(s, shot, 0.6, 1.55, 6.35, 2.75)
            screenshot(s, second, 0.6, 4.45, 6.35, 2.5)
        else:
            screenshot(s, shot, 0.6, 1.75, 6.4, 4.9)
        tx = 7.3; txw = 5.4
        text(s, tx, 1.72, txw, 0.9, [[(desc, 14.5, False, MUTED, BODY)]], line_spacing=1.05)
        bullets(s, tx, 2.62, txw, blist, size=14.5)
    footer(s, num)
    notes(s, notes_txt)
    return s

# =================================================================== SLIDE 5 — CITIZEN DASHBOARD
content_slide(5, "Citizen Dashboard", "Every citizen’s cases in one place",
    "After registering, citizens get a personal, secure dashboard for all their consular requests.",
    os.path.join(SHOTS, "04-citizen-dashboard.png"),
    ["Clear totals: filed, active, resolved, archived",
     "Every complaint with its live status and tracking code",
     "File a new complaint or request in one click",
     "Private — each citizen sees only their own cases"],
    shot_side="right",
    notes_txt="Once a citizen registers and verifies their email, they land on this personal dashboard. It summarises "
        "everything they have filed — total, active, resolved and archived — and lists each case with its live "
        "status and unique tracking code. They can file a new request in one click. Importantly, access is strictly "
        "private: a citizen sees only their own cases, enforced by the system’s role-based permissions.")

# =================================================================== SLIDE 6 — APPOINTMENT SYSTEM
content_slide(6, "Appointment System", "Book the right service, prepared",
    "Citizens choose a mission and service, see real available time slots, and know exactly what to bring.",
    os.path.join(SHOTS, "06-required-documents.png"),
    ["Select country, mission, service and time slot",
     "Required documents shown before booking",
     "Each mission has its own calendar of slots",
     "No double-booking; full slots move to a waitlist",
     "QR-coded confirmation for the visit"],
    shot_side="left",
    notes_txt="Appointments are a core service. The citizen selects a mission and the service they need, and the system "
        "shows the real available time slots for that mission’s own calendar. Crucially, before they book, the "
        "required documents are listed — so they never travel unprepared and get turned away. The system prevents "
        "double-booking: if a slot is full, the citizen is automatically placed on a waitlist. Each confirmed "
        "appointment carries a QR code for check-in.")

# =================================================================== SLIDE 7 — COMPLAINT MANAGEMENT
content_slide(7, "Complaint Management", "A transparent complaint workflow",
    "Citizens raise issues and follow them from submission to resolution — with an official response.",
    os.path.join(SHOTS, "07-complaint.png"),
    ["Submit by category, with evidence and optional anonymity",
     "Receive a secure 8-character tracking code",
     "Follow a live status timeline to resolution",
     "Read the mission’s official public response",
     "Rate the resolution to inform service quality"],
    shot_side="right", second=os.path.join(SHOTS, "09-track-case.png"),
    notes_txt="Complaints follow a transparent workflow. A citizen submits by category, can attach evidence, and may "
        "submit anonymously. They receive a secure eight-character tracking code and can follow a live status timeline "
        "— submitted, assigned, under review, resolved — shown on the right. When the mission responds, the "
        "official public response appears on the tracking page, and the citizen can rate the resolution, which feeds "
        "the Ministry’s service-quality metrics.")

# =================================================================== SLIDE 8 — EMERGENCY
content_slide(8, "Emergency Assistance", "A fast, prioritised channel for crises",
    "A prominent emergency channel routes urgent cases straight to mission and Ministry attention.",
    os.path.join(SHOTS, "08-emergency.png"),
    ["Typed crises: medical, detention, trafficking, lost passport, and more",
     "Server-validated intake so no critical detail is missed",
     "Automatically flagged CRITICAL priority",
     "Pinned at the top of staff and Ministry dashboards",
     "Hardship factors captured for faster triage"],
    shot_side="left",
    notes_txt="In an emergency, speed matters. The platform has a prominent emergency channel with clearly typed crisis "
        "categories — medical, arrest or detention, human trafficking, lost passport, domestic violence and more. "
        "The intake is validated so critical details are never missed, and every emergency is automatically flagged as "
        "CRITICAL priority. As we will see on the dashboards, these cases are pinned at the top of both mission and "
        "Ministry screens so they are actioned before routine work.")

# =================================================================== SLIDE 9 — COMMUNITY ORGS
content_slide(9, "Community Organisations", "Verified community support, officially recognised",
    "Somali student associations and community groups register, are verified, and connect citizens to help.",
    os.path.join(SHOTS, "10-community-profile.png"),
    ["Student associations, community groups and volunteers",
     "Self-registration with a verified / pending status",
     "Only Ministry-verified organisations appear publicly",
     "Profiles show services, languages and emergency support",
     "Organisations manage their own profile, events and messages"],
    shot_side="right", second=os.path.join(SHOTS, "11-community-events.png"),
    notes_txt="Beyond the missions themselves, a strong diaspora support network already exists — student "
        "associations, community groups, volunteers who offer translation, accommodation and legal guidance. The "
        "platform lets these organisations register themselves and be officially verified by the Ministry. Only "
        "verified organisations appear to the public. Each manages its own profile, announcements and events through "
        "the self-service panel on the right, while the Ministry retains full oversight and moderation.")

# =================================================================== SLIDE 10 — EVENTS
content_slide(10, "Community & Consular Events", "Bringing services closer to citizens",
    "Missions publish Passport Days, mobile consular services and awareness sessions citizens can find and join.",
    os.path.join(SHOTS, "18-events.png"),
    ["Passport Days and mobile consular services",
     "Student orientations and document-guidance sessions",
     "Emergency-awareness and community meetings",
     "Filter upcoming events by country, city and mission",
     "Registration links and capacity shown up front"],
    shot_side="left",
    notes_txt="The platform also promotes public engagement. Missions and the Ministry publish consular events — "
        "Passport Days, mobile consular services that travel to where citizens are, student orientations, document "
        "guidance and emergency-awareness sessions. Citizens can filter upcoming events by country, city and mission, "
        "see capacity, and register. This brings services physically closer to communities and strengthens the "
        "relationship between citizens and their missions.")

# =================================================================== SLIDE 11 — EMBASSY DASHBOARD
content_slide(11, "Embassy Dashboard", "Everything a mission needs to serve and respond",
    "Embassy officers and managers get a scoped workspace for their own mission’s cases and performance.",
    os.path.join(SHOTS, "12-embassy-dashboard.png"),
    ["Active emergency / critical cases pinned at the top",
     "Live metrics: volume, resolution rate, response time, satisfaction",
     "Case assignment and status management",
     "SLA targets and response deadlines in view",
     "Staff see only their own mission’s data"],
    shot_side="right",
    notes_txt="This is the embassy staff workspace. The first thing an officer sees is the red band of active emergency "
        "and critical cases, which must be handled before routine work. Above the case list are live performance metrics "
        "— volume, resolution rate, average response time and citizen satisfaction — alongside SLA targets. "
        "Managers can assign cases to officers and manage status. Access is mission-scoped: staff see only the cases and "
        "data for their own mission, never another’s.")

# =================================================================== SLIDE 12 — MINISTRY DASHBOARD
content_slide(12, "Ministry Dashboard", "National oversight in real time",
    "The Ministry sees the whole network — crises, delays, and performance — on one command centre.",
    os.path.join(SHOTS, "13-ministry-dashboard.png"),
    ["Critical crisis queue across every mission",
     "SLA escalation alerts for delayed cases",
     "Global distribution & performance map",
     "Review and moderate community organisations & content",
     "Full national visibility for reviewers and administrators"],
    shot_side="left", second=os.path.join(SHOTS, "14-admin-dashboard.png"),
    notes_txt="At the national level, the Ministry gets an operations command centre. It shows the critical crisis "
        "queue across every mission, SLA escalation alerts for cases that are running late, and a global map of "
        "distribution and performance. The second screen is the moderation console, where the Ministry verifies "
        "community organisations and approves their announcements and events before anything is shown publicly. "
        "Ministry reviewers and administrators have full national visibility, according to their role.")

# =================================================================== SLIDE 13 — TRANSPARENCY & ANALYTICS
content_slide(13, "Transparency & Analytics", "Evidence for better decisions and public trust",
    "Rich analytics for the Ministry and an open transparency portal for the public — from the same live data.",
    os.path.join(SHOTS, "16-analytics.png"),
    ["Complaints by mission, country and category",
     "Resolution time, satisfaction and SLA compliance",
     "Submission trends over time",
     "Public transparency portal with mission rankings",
     "Export to CSV, Excel and PDF for reporting"],
    shot_side="right", second=os.path.join(SHOTS, "15-transparency.png"),
    notes_txt="All of this activity produces evidence. For the Ministry, the analytics dashboard breaks down complaints "
        "by mission, country and category, and tracks resolution time, satisfaction and SLA compliance over time. For "
        "the public, the transparency portal — the lower image — publishes mission rankings and resolution "
        "outcomes from the same live data. Reports can be exported to CSV, Excel and PDF. Transparency is not a slogan "
        "here; it is built into the product.")

# =================================================================== SLIDE 14 — SECURITY
s = slide(NAVY)
kicker(s, 0.6, 0.55, "Security & Data Protection", ICE)
title(s, 0.6, 0.92, "Built to protect citizens’ information", WHITE)
text(s, 0.6, 1.72, SW - 1.2, 0.5, [[("Security and privacy are designed into the platform, not added afterwards.", 15, False, ICE, BODY)]])
secs = [
    ("Role-based access", "Six roles — citizen, officer, manager, reviewer, administrator, community — each see only what they should."),
    ("Mission-scoped data", "Staff access is limited to their own mission; cross-mission access is blocked and tested."),
    ("Audit logging", "Logins, exports and case actions are recorded with time, user and IP for accountability."),
    ("Data privacy", "Anonymous complaints store no identity; the public sees only aggregate, approved information."),
    ("Secure authentication", "Hashed passwords, email verification, brute-force lockout and CSRF protection."),
    ("Safe uploads", "Evidence and logos are validated by type and size before they are stored."),
]
gx, gy, cw, ch, gapx, gapy = 0.6, 2.3, 3.95, 1.95, 0.22, 0.2
for i, (h, d) in enumerate(secs):
    r, cc = divmod(i, 3)
    x = gx + cc * (cw + gapx); y = gy + r * (ch + gapy)
    card(s, x, y, cw, ch, fill=RGBColor(0x1C,0x35,0x54), line=RGBColor(0x2C,0x48,0x6B), shadow=False)
    chip(s, x + 0.28, y + 0.28, 0.44, PRIMARY, str(i + 1), WHITE, 16)
    text(s, x + 0.28, y + 0.84, cw - 0.56, 0.4, [[(h, 14.5, True, WHITE, BODY)]])
    text(s, x + 0.28, y + 1.2, cw - 0.56, 0.7, [[(d, 11, False, ICE, BODY)]], line_spacing=1.02)
footer(s, 14, dark=True)
notes(s, "For a government platform handling citizen data, security is foundational. Access is role-based: six distinct "
         "roles each see only what they should. Staff data is mission-scoped — an officer in one country cannot see "
         "another mission’s cases, and this is enforced and tested. Sensitive actions are recorded in an audit log "
         "with user, time and IP. Anonymous complaints store no identifying data, and the public only ever sees "
         "aggregate, approved information. Authentication uses hashed passwords, email verification and brute-force "
         "lockout, and all uploads are validated. Some items — an independent penetration test and live TLS — "
         "remain for the deployment phase, and I will be transparent about that.")

# =================================================================== SLIDE 15 — BENEFITS
s = slide(LIGHT)
kicker(s, 0.6, 0.55, "Benefits")
title(s, 0.6, 0.92, "Value for everyone the Ministry serves")
bens = [
    ("Citizens", "Faster service, clear requirements, and visibility of their own cases — in their language."),
    ("Embassies", "A single organised workspace, prioritised emergencies, and less manual follow-up."),
    ("The Ministry", "Real-time national oversight, evidence-based decisions, and measurable service quality."),
    ("Government", "A modern, transparent public service that strengthens institutional credibility."),
    ("The Diaspora", "A trusted connection to home — community networks, events, and responsive support."),
]
gx, gy, cw, ch, gapx = 0.6, 2.15, 2.35, 3.0, 0.16
for i, (h, d) in enumerate(bens):
    x = gx + i * (cw + gapx)
    card(s, x, gy, cw, ch)
    chip(s, x + cw/2 - 0.32, gy + 0.35, 0.64, RGBColor(0xE7,0xEF,0xF9), str(i + 1), PRIMARY, 20)
    text(s, x + 0.22, gy + 1.2, cw - 0.44, 0.45, [[(h, 15.5, True, NAVY, BODY)]], align=PP_ALIGN.CENTER)
    text(s, x + 0.24, gy + 1.72, cw - 0.48, 1.2, [[(d, 11.5, False, MUTED, BODY)]], align=PP_ALIGN.CENTER, line_spacing=1.05)
footer(s, 15)
notes(s, "The benefits reach every stakeholder. Citizens get faster service, know what to bring, and can see their own "
         "cases in their own language. Embassies get one organised workspace with emergencies prioritised and less "
         "manual follow-up. The Ministry gains real-time national oversight and evidence for decisions. For the "
         "Government, it is a modern, transparent public service that strengthens credibility. And for the diaspora, it "
         "is a trusted connection to home. Everyone the Ministry serves is better off.")

# =================================================================== SLIDE 16 — FUTURE VISION
s = slide(LIGHT)
kicker(s, 0.6, 0.55, "Future Vision")
title(s, 0.6, 0.92, "A foundation ready to grow")
text(s, 0.6, 1.72, SW - 1.2, 0.5, [[("The platform is architected so these enhancements can be added without rebuilding.", 15, False, MUTED, BODY)]])
future = [
    ("Smart AI Assistant", "Upgrade the built-in guided assistant to AI-powered answers over consular knowledge."),
    ("Mobile App", "Native apps building on the existing REST API for an even richer citizen experience."),
    ("SMS Notifications", "Reach citizens without email; the notification channel is already interface-ready."),
    ("WhatsApp Updates", "Case and appointment updates on the channel citizens use most."),
    ("Digital Identity", "Integrate national digital ID for stronger verification and pre-filled services."),
    ("Smart Analytics", "Predictive insight on demand, bottlenecks and emerging consular needs."),
]
gx, gy, cw, ch, gapx, gapy = 0.6, 2.35, 3.95, 1.9, 0.22, 0.2
for i, (h, d) in enumerate(future):
    r, cc = divmod(i, 3)
    x = gx + cc * (cw + gapx); y = gy + r * (ch + gapy)
    card(s, x, y, cw, ch)
    chip(s, x + 0.28, y + 0.28, 0.44, RGBColor(0xE7,0xEF,0xF9), "→", PRIMARY, 18)
    text(s, x + 0.28, y + 0.84, cw - 0.56, 0.4, [[(h, 14.5, True, NAVY, BODY)]])
    text(s, x + 0.28, y + 1.2, cw - 0.56, 0.7, [[(d, 11, False, MUTED, BODY)]], line_spacing=1.02)
footer(s, 16)
notes(s, "This is a foundation, not a finished endpoint. The architecture is deliberately built to grow. The guided "
         "citizen assistant can be upgraded to AI-powered answers. The existing REST API means native mobile apps can "
         "follow. The notification system is already interface-ready for SMS and WhatsApp, so we can reach citizens on "
         "the channels they actually use. Longer term, integration with national digital identity and predictive "
         "analytics. Each of these is an addition, not a rebuild — which protects the Ministry’s investment.")

# =================================================================== SLIDE 17 — CONCLUSION
s = slide(NAVY)
s.shapes.add_picture(COAT, Inches(SW/2 - 0.62), Inches(0.85), height=Inches(1.24))
kicker(s, 1, 2.45, "Conclusion", ICE)
text(s, 1, 2.9, SW - 2, 2.0,
     [[("Modernising Somali consular services,", 34, True, WHITE, HEAD)],
      [("serving citizens worldwide.", 34, True, WHITE, HEAD)]],
     align=PP_ALIGN.CENTER, line_spacing=1.05)
text(s, 1.5, 4.95, SW - 3, 1.2,
     [[("A working, secure, bilingual platform that connects citizens, missions and the Ministry — "
        "ready for demonstration and staging today, and built to grow into the Ministry’s digital future.",
        15.5, False, ICE, BODY)]], align=PP_ALIGN.CENTER, line_spacing=1.15)
footer(s, 17, dark=True)
notes(s, "To conclude: this platform modernises Somali consular services around the citizen. It is a real, working, "
         "secure and bilingual system that connects citizens, missions and the Ministry on one network. It is ready to "
         "demonstrate and to run in a staging environment today. A short list of items remains for full public launch "
         "— production hosting, a live security certificate, an independent penetration test and a native Somali "
         "language review — and I can walk you through that plan. Thank you for the opportunity to present it.")

# =================================================================== SLIDE 18 — THANK YOU
s = slide(NAVY)
s.shapes.add_picture(COAT, Inches(SW/2 - 0.8), Inches(1.35), height=Inches(1.6))
text(s, 1, 3.3, SW - 2, 1.0, [[("Thank You", 44, True, WHITE, HEAD)]], align=PP_ALIGN.CENTER)
text(s, 1, 4.4, SW - 2, 0.5, [[("Questions & Discussion", 18, False, ICE, BODY, True)]], align=PP_ALIGN.CENTER)
text(s, 1, 5.5, SW - 2, 0.8,
     [[("Ministry of Foreign Affairs  •  Federal Republic of Somalia", 13, True, WHITE, BODY)],
      [("Digital Consular Services Platform", 11.5, False, RGBColor(0x9F,0xB2,0xC8), BODY)]],
     align=PP_ALIGN.CENTER, space_after=2)
notes(s, "Thank you. I welcome your questions, and I would be glad to give a live walkthrough of any part of the "
         "platform — booking an appointment, submitting an emergency case, or the Ministry oversight dashboards "
         "— on request.")

prs.save(OUT)
print("Saved:", OUT, "| slides:", len(prs.slides._sldIdLst))
