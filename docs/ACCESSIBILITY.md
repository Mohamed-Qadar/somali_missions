# Accessibility Statement

The Somali Missions platform aims to conform to **WCAG 2.1 Level AA**, so that citizens with disabilities can find missions, submit and track complaints, book appointments, and use every citizen-facing feature.

## What has been done

- **Automated auditing**: every key page is tested with **axe-core** (WCAG 2 A/AA rule set). At the time of writing, the audited citizen- and staff-facing pages (home, directory, before-you-travel, appointments, queue, assistant, complaint submission, tracking, transparency, citizen dashboard, ministry analytics, ministry operations) report **zero** violations.
- **Colour contrast**: the brand palette was measured and darkened where needed so text meets the 4.5:1 (normal) / 3:1 (large) AA thresholds — including badges on tinted backgrounds and large statistic numbers.
- **Keyboard & screen reader**: a skip-to-content link; `aria-label`s on icon-only controls and all form filters; `aria-expanded`/`aria-controls` on the nav toggle and profile menu; visible focus rings; `tabindex`/`role`/`aria-label` on scrollable message and data panels so keyboard users can reach and scroll them.
- **Forms**: every input is associated with a label (explicit `for`/`id`), and validation errors are shown as text, not colour alone.
- **Structure**: semantic landmarks (`header`/`main`/`nav`/`contentinfo`), a single `<h1>` per page, and `{% empty %}` states so screen readers aren't left on blank regions.
- **Responsive**: no horizontal scrolling at mobile (375px) or tablet (768px) widths; a working mobile menu.
- **Bilingual**: full English and Somali support with a persistent language switcher.

## Regression protection

New pages are expected to pass an axe-core run before merge (see [CONTRIBUTING.md](../CONTRIBUTING.md)). Colour choices go through the compiled Tailwind theme in `tailwind.config.js`, keeping the AA-compliant palette in one place.

## Known limitations

- Automated tooling (axe-core) catches most but not all issues. A **manual audit with real assistive technology** (screen readers such as NVDA/VoiceOver, voice control, full keyboard-only walkthroughs) and, ideally, testing with disabled users has not yet been performed and should be done before a formal accessibility certification.
- The embedded Leaflet map is a third-party control; its attribution links are made distinguishable, but full map interaction may not be equally usable by all assistive technologies — the same information (mission address/contact) is always available as text on the mission page.

## Reporting an accessibility problem

Please contact the Ministry (see the Contact page) or email **accessibility@mfa.gov.so** (replace with the real contact before launch) describing the page and the barrier you encountered. We treat accessibility barriers as bugs.
