# Embassy/Consulate Staff Guide

Your account is scoped to **one mission only** - you cannot see or act on another mission's complaints, appointments, or queue. This is enforced on every page and API endpoint, not just hidden in the UI.

## Getting an account

A Ministry Administrator invites you (Ministry dashboard → Invite New Embassy User) by email. You'll receive an activation link to set your username/password; your role (Embassy Officer or Embassy Manager) and mission are set by the Ministry when they send the invite.

## Complaints

- **Staff Dashboard** (`/staff/`) lists your mission(s) with a link into each one's complaint queue.
- Inside a mission, select a complaint to update its status or write a response. Public responses (checkbox) appear on the citizen's tracking page; keep internal notes for anything not meant for the citizen.
- The **Embassy Dashboard** (`/dashboard/embassy/`) has the fuller case workspace, including the secure message thread with the citizen and audit history for the case.

## Appointments

- **Appointments** (linked from the staff dashboard) shows daily/weekly/monthly views for your mission.
- **Approve/Reject/Reschedule/Cancel/Complete/No-Show** each transition is logged and, if the citizen has an account, triggers a notification.
- **Manage Slots** lets you define available time slots per service (date, time range, and how many appointments it can hold - this is what "no double booking" is enforced against).
- **Waitlist** shows citizens waiting for a full slot to free up.

## Queue

- **Queue** shows today's walk-in tickets for your mission.
- **Call Next** serves the next-highest-priority waiting ticket (auto-completes whoever was still marked "serving").
- Open the **Display Screen** on a lobby monitor - it shows "now serving" and auto-refreshes every 10 seconds.
- **Skip** / **Recall** / **Complete** / **No-Show** manage individual tickets.

## Notifications

The bell icon (top right, when logged in) shows your unread count. Ministry-wide emergency broadcasts also arrive here if targeted at all staff.
