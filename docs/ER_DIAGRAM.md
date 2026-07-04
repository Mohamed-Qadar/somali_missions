# Entity-Relationship Diagram

Focused on the core entities and their relationships. Field lists are trimmed to what matters for understanding the data model - see `missions/models.py`, `appointments/models.py`, `queue_management/models.py`, `assistant/models.py`, `notifications/models.py` for full field definitions.

```mermaid
erDiagram
    USER ||--|| USERPROFILE : has
    USERPROFILE }o--o| MISSION : "scoped to (if staff)"

    MISSION ||--o{ MISSIONSERVICE : offers
    MISSIONSERVICE ||--o{ REQUIREDDOCUMENT : requires
    MISSION ||--o{ EMERGENCYSUPPORTCONTACT : has
    MISSION }o--o{ USER : "staff_users (M2M)"

    MISSION ||--o{ COMPLAINT : receives
    COMPLAINT }o--o| USER : "citizen_user (nullable - anonymous)"
    COMPLAINT }o--o| USER : "assigned_officer"
    COMPLAINT ||--o{ COMPLAINTEVIDENCE : "has attachments"
    COMPLAINT ||--o{ COMPLAINTSTATUSHISTORY : "status changes"
    COMPLAINT ||--o{ EMBASSYRESPONSE : "official responses"
    COMPLAINT ||--o{ SECUREMESSAGE : "citizen<->staff chat"
    COMPLAINT ||--o{ ESCALATIONLOG : escalations
    COMPLAINT ||--o{ AUDITLOG : "logged actions (optional link)"

    MISSION ||--o{ APPOINTMENTSLOT : defines
    APPOINTMENTSLOT ||--o{ APPOINTMENT : "booked into (capacity-limited)"
    APPOINTMENT }o--o| USER : "citizen_user (nullable)"
    APPOINTMENT ||--o{ APPOINTMENTSTATUSHISTORY : "status changes"
    APPOINTMENT ||--o{ QUEUETICKET : "optional link"

    MISSION ||--o{ QUEUETICKET : "walk-in tickets"

    ASSISTANTTOPIC ||--o{ ASSISTANTCONVERSATIONLOG : "matched by"

    USER ||--o{ NOTIFICATION : receives
    NOTIFICATION ||--o{ NOTIFICATIONDELIVERYLOG : "delivery attempts per channel"

    COMMUNITYGROUP ||--o{ COMMUNITYEVENT : hosts
    COMMUNITYGROUP ||--o{ COMMUNITYANNOUNCEMENT : posts
    COMMUNITYGROUP ||--o{ COMMUNITYREPRESENTATIVE : "run by"
    STUDENTASSOCIATION ||--o{ COMMUNITYEVENT : hosts
    STUDENTASSOCIATION ||--o{ COMMUNITYANNOUNCEMENT : posts
    STUDENTASSOCIATION ||--o{ COMMUNITYREPRESENTATIVE : "run by"

    MISSION {
        string name
        string country
        string city
        string mission_type "EM or CO"
        decimal latitude
        decimal longitude
    }
    USERPROFILE {
        string role "CITIZEN, EMBASSY_OFFICER, EMBASSY_MANAGER, MINISTRY_REVIEWER, MINISTRY_ADMIN, COMMUNITY_REP"
        bool email_verified
    }
    COMPLAINT {
        string tracking_code "8-char CSPRNG, unique"
        string status
        string category
        int rating "1-5"
        bool is_anonymous
        string sentiment
    }
    APPOINTMENTSLOT {
        date date
        time start_time
        time end_time
        int capacity
    }
    APPOINTMENT {
        string qr_token "10-char CSPRNG, unique"
        string status "PENDING, CONFIRMED, WAITLISTED, ..."
    }
    QUEUETICKET {
        int ticket_number "sequential per mission per day"
        string status "WAITING, SERVING, COMPLETED, ..."
        int priority
    }
    ASSISTANTTOPIC {
        string topic_key
        string keywords "comma-separated"
        text answer
        string suggested_action
    }
    NOTIFICATION {
        string title
        string category "INFO, SUCCESS, WARNING, EMERGENCY"
        bool is_read
    }
    AUDITLOG {
        string action
        string ip_address
        string user_agent
        datetime timestamp
    }
```

## Notes on design choices

- **Tracking codes and QR tokens** are generated with `secrets.choice` (CSPRNG), not sequential IDs - unguessable, so knowing one code doesn't help you enumerate others. See `Complaint.tracking_code` / `Appointment.qr_token`.
- **Anonymous complaints**: `Complaint.citizen_user` is nullable; when `is_anonymous=True`, `full_name`/`email`/`phone` are blanked on save (see `Complaint.save()`) rather than just hidden in the UI - the PII genuinely isn't retained.
- **Dual staff-scoping paths**: a user can be scoped to a mission either via `Mission.staff_users` (M2M, set by Django Group-based provisioning) or via `UserProfile.mission` + `UserProfile.role` (set by the invitation flow). Both are checked everywhere via `missions/utils/permissions.py` - see [ARCHITECTURE.md](ARCHITECTURE.md).
- **AuditLog.complaint is nullable** - it started as complaint-only, then was extended (migration 0008) to also log account-level events (login, role changes, exports) with no associated complaint.
