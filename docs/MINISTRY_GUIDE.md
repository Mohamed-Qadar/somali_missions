# Ministry Guide

Ministry Reviewer and Ministry Administrator accounts see **every mission's** data - complaints, appointments, and queue activity worldwide, not just one mission.

## Operations dashboard

`/ministry/operations/` — the command-center view: critical/urgent complaints needing attention, SLA escalation alerts (complaints unresolved past their target time), a world map of mission activity, and the global escalation action log.

## Analytics

`/ministry/analytics/` — pick a period (30 days / 365 days / all time) to see:

- Complaints by mission, by country, by category, and monthly trend charts
- Average resolution time and satisfaction rate
- **Complaints handled per officer**
- A **country × month heatmap** of complaint volume
- Today's real average appointment/queue wait times (not estimates)

Export the underlying complaint data as **CSV**, **Excel**, or a formatted **PDF** report from `/reports/`.

## Managing embassy staff

`/ministry/invite/` (Ministry Administrator only) — invite a new embassy officer or manager by email, assigning them to a specific mission. They'll get an activation link to set up their own account; you don't set their password.

To adjust an existing user's role or mission assignment directly, use the Django admin (`/admin/missions/userprofile/`).

## Public transparency portal

`/transparency/` is public - it shows aggregate mission performance (ratings, resolution rates, top/bottom performers) and anonymized "resolution success stories," with no citizen-identifying information. This is what citizens and the public see; you don't need to do anything to maintain it, it's computed live (cached 5 minutes) from real complaint data.

## Emergency broadcast

`/notifications/emergency-broadcast/` (Ministry Administrator only) — send a critical notification (in-app + email) to all embassy staff, all registered citizens, or everyone. Use only for genuine emergencies; every broadcast is logged in the audit log.

## Admin panel

`/admin/` gives full CRUD access to every model, including `UserProfile` (role/mission assignment), `EmbassyInvitation` (pending invites), and `SecureMessage` (citizen↔staff conversations) - useful for support/debugging tasks the regular UI doesn't expose.
