# Django Admin Guide

`/admin/` is available to superusers and any account with `is_staff=True` (in practice: superusers and the seeded `ministry_admin` account - regular embassy staff never get Django-admin access, only their scoped dashboards).

## What's registered

| Model | Notes |
|---|---|
| `Mission`, `MissionService`, `RequiredDocument`, `EmergencySupportContact` | Mission directory data |
| `Complaint` | `is_anonymous` shown in the list so you can tell at a glance which cases are anonymous; date-hierarchy navigation by `created_at` |
| `UserProfile` | Edit role/mission assignment directly - the only UI for this besides the invitation flow |
| `EmbassyInvitation` | Pending/used invitations |
| `SecureMessage` | Citizen↔staff message threads (read-only support/debugging use) |
| `CommunityGroup`, `StudentAssociation` + their events/announcements/representatives | Bulk actions: mark verified, suspend, approve+publish |
| `AppointmentSlot`, `Appointment`, `AppointmentStatusHistory` | Full appointment history |
| `QueueTicket` | Today's and historical walk-in tickets |
| `AssistantTopic`, `AssistantConversationLog` | Edit the assistant's keyword/answer knowledge base; review what citizens are actually asking |
| `Notification`, `NotificationDeliveryLog` | See exactly which channel(s) a notification went through and whether each one actually delivered |
| `AuditLog` | Every login/logout/failed-login/complaint-action/appointment-action/queue-action/role-change/export, with IP + user agent |
| `MissionPerformanceScore`, `EscalationRule`, `EscalationLog`, `ContactMessage` | Supporting operational data |

## Common tasks

**Fix a user's role or mission assignment**: `/admin/missions/userprofile/`, edit the `role` and `mission` fields directly. This is the same data the invitation flow sets - editing it here has an identical effect.

**Investigate a security concern**: `/admin/missions/auditlog/`, filter by `action`, search by username or IP. Every login attempt (including failures) is here with the source IP and browser user-agent.

**Update the assistant's answers**: `/admin/assistant/assistanttopic/`. Keywords are comma-separated; matching requires every word in a keyword phrase to appear in the citizen's question (see [ARCHITECTURE.md](ARCHITECTURE.md) for why - it's what makes "lost passport" beat the generic "passport" keyword).

**Moderate community groups**: `/admin/missions/communitygroup/` or `/studentassociation/` - select rows and use the "Mark selected groups as verified" / "Suspend" bulk actions.
