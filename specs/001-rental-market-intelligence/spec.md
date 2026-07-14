# Feature Specification: Rental Market Intelligence

**Feature Branch**: `001-rental-market-intelligence`

**Created**: 2026-07-13

**Status**: Draft

**Input**: User description: "Application that continuously monitors apartment rental listings within a
configurable geographic area and provides pricing recommendations, market insights, and competitive
analysis for a specific apartment. The product answers: 'Given today's market, what should I list
my apartment for and why?'"

## User Scenarios & Testing

<!--
  User stories are prioritized as independent journeys ordered by importance.
  Each story is independently testable and delivers standalone value.
-->

### User Story 1 - Get a Pricing Recommendation (Priority: P1)

A landlord who wants to rent their Berlin apartment enters their property details into the platform.
Within seconds, they receive a recommended listing price along with a plain-language explanation of
why that price makes sense — referencing factors like comparable apartment prices, neighborhood
demand, and seasonal trends.

**Why this priority**: This is the core value proposition — "what should I list my apartment for
and why?" Without this, no other story delivers value.

**Independent Test**: Enter a Berlin apartment's details and verify a recommended price with
explanation is returned. The feature is complete and useful even with no other stories implemented.

**Acceptance Scenarios**:

1. **Given** a landlord enters their apartment's location (Berlin neighborhood or postal code),
   size (m²), number of rooms, floor, and key amenities, **When** they request a pricing
   recommendation, **Then** the system returns a recommended monthly rent in EUR with a confidence
   range (e.g., €1,200–€1,350) and a plain-language explanation covering at least 3 market factors.

2. **Given** fewer than 5 comparable apartments exist in the landlord's area, **When** they request
   a recommendation, **Then** the system returns the best available estimate and clearly indicates
   the recommendation has lower confidence due to limited market data.

3. **Given** market data is more than 48 hours old, **When** a recommendation is requested, **Then**
   the system flags that data may be stale and shows the data freshness timestamp.

---

### User Story 2 - View Comparable Listings (Priority: P2)

A landlord can see the specific apartments the system used as comparables when generating their
pricing recommendation — including price, size, room count, and proximity to their property. This
gives them confidence in the recommendation and lets them do their own sanity check.

**Why this priority**: Transparency builds trust. Landlords are making a financially significant
decision and need to verify the data behind the recommendation.

**Independent Test**: After requesting a recommendation, view the comparable listings panel. Delivers
standalone value as a market research view even without other stories.

**Acceptance Scenarios**:

1. **Given** a pricing recommendation has been generated, **When** the landlord views comparable
   listings, **Then** at least 5 listings are shown with price (EUR/month), size (m²), room count,
   distance from the landlord's apartment, and source platform name.

2. **Given** a landlord views a comparable listing entry, **When** they click through to the
   original listing, **Then** they are taken to the source listing page on immobilienscout24.de
   (or the originating platform).

---

<!--
  POST-MVP: User Story 3 - Monitor Market Changes Over Time

  Deferred because it depends on FR-F001 (historical snapshots), FR-F002 (price change
  notifications), and FR-F003 (saved apartment profiles) — all of which are post-MVP.

  ### User Story 3 - Monitor Market Changes Over Time (Priority: P3)

  A landlord who has saved their apartment profile can view how their recommended listing price has
  evolved over time as the market changes — and receives a notification when a significant shift
  occurs (e.g., "the recommended price for your apartment increased by €50 this month due to
  reduced supply in Mitte").

  **Why this priority**: Ongoing monitoring transforms a one-time recommendation into a persistent
  intelligence service — the "continuously monitors" part of the core proposition.

  **Independent Test**: Verify that daily market snapshots are captured and a historical price
  trend chart renders for a saved apartment profile.

  **Acceptance Scenarios**:

  1. Given a landlord has a saved apartment profile, When they view the market trends dashboard,
     Then they see a price trend chart showing their recommended price over the past 30, 60,
     and 90 days.

  2. Given the recommended price for a saved apartment changes by more than 5% since the last
     notification, When the next market refresh completes, Then the landlord receives a
     notification explaining the change and the key factors driving it.
-->

---

### User Story 4 - Configure Geographic Monitoring Area (Priority: P4)

A landlord can define the geographic scope of the market data the platform collects — choosing
Berlin neighborhoods (Kieze), postal codes, or a radius around their apartment address.

**Why this priority**: Berlin rental markets vary dramatically by neighborhood. Landlords need
data scoped to their specific area for recommendations to be meaningful.

**Independent Test**: Configure a monitoring area by postal code and verify that only listings
within that area are returned in comparables and market statistics.

**Acceptance Scenarios**:

1. **Given** a landlord specifies a Berlin postal code or neighborhood as their monitoring area,
   **When** the system collects market data, **Then** only listings within that area are included
   in comparables and market statistics.

2. **Given** a landlord updates their monitoring area, **When** they request a new recommendation,
   **Then** the system recalculates using listings from the updated area only, and the previous
   area's data is no longer used.

---

### Edge Cases

- What happens when fewer than 5 comparable apartments exist in the configured area? (thin market —
  return best estimate with explicit low-confidence warning)
- What happens when an apartment has unusual characteristics (>200m², 6+ rooms)? (wider confidence
  range, flagged as atypical market segment)
- What if a CSV upload contains malformed rows? (skip invalid rows, report a count of skipped entries
  to the uploader; do not abort the entire import)
- What if a CSV upload contains listings already in the database? (deduplicate by source URL and
  listing date; do not create duplicate records)
- What if no CSV has been uploaded yet? (show a clear empty-state prompt guiding the operator
  to upload data before recommendations can be generated)
- What if the uploaded CSV contains listings outside the configured Berlin area? (exclude out-of-area
  listings from comparables; still import them for future use)

## Requirements

### Functional Requirements (MVP)

- **FR-001**: The system MUST provide a CSV import interface that accepts rental listing data
  exported from an external collection tool (e.g., Fredy), with a defined and documented column
  schema (title, address, price in EUR/month, size in m², room count, floor, source URL,
  listing date, source platform)
- **FR-002**: On CSV upload, the system MUST validate, normalize, and deduplicate listings —
  skipping malformed rows with a reported count, rejecting duplicate records by source URL and
  listing date, and standardizing price and size units
- **FR-003**: The system MUST allow landlords to input their apartment's characteristics: location
  (Berlin address or postal code), size in m², number of rooms, floor, and key amenities (balcony,
  parking, elevator, furnished)
- **FR-004**: The system MUST identify comparable listings from the imported dataset based on
  proximity, size range (±20% of the landlord's apartment), and room count (±1 room)
- **FR-005**: The system MUST calculate a recommended listing price using statistical analysis of
  comparable listings (median and percentile distribution)
- **FR-006**: The system MUST generate a natural language explanation of the pricing recommendation
  citing at least 3 specific market factors (e.g., neighborhood supply level, seasonal trend,
  price distribution of comparables)
- **FR-007**: The system MUST display a competitive analysis showing where the recommended price
  sits relative to current comparable listings (e.g., "60th percentile for your area")
- **FR-008**: The system MUST allow landlords to filter comparables by Berlin neighborhood name
  or postal code
- **FR-009**: The system MUST display a data freshness indicator showing when the most recent
  CSV upload occurred and how many listings are currently in the dataset

### Future Requirements (Post-MVP)

<!--
  The following requirements are deferred from MVP scope.
  Re-promote to Functional Requirements when prioritized for a future release.
-->

<!-- FR-F001: The system MUST retain historical market snapshots to enable price trend analysis
  over a minimum of 90 days -->

<!-- FR-F002: The system MUST notify landlords when their recommended price changes by more than
  5% between consecutive market refreshes -->

<!-- FR-F003: The system MUST allow landlords to save their apartment profile so that monitoring
  and notifications persist between sessions — [NEEDS CLARIFICATION: Should profile saving require
  user account registration (email + password), or can it be achieved via a shareable link or
  browser-local storage without account creation?] -->

### Key Entities

- **Apartment Profile**: Landlord's property — address/location, size (m²), room count, floor,
  amenities list
- **Listing**: A rental listing imported from a CSV upload — source platform, source URL, asking
  price (EUR/month), size (m²), room count, floor, address, listing date, import batch reference
- **Import Batch**: A single CSV upload event — upload timestamp, total rows received, rows
  imported, rows skipped (with reasons), uploader identity
- **Comparable Set**: The filtered subset of listings used for a specific recommendation — filter
  criteria applied (area, size range, room count), listings included, generated date
- **Pricing Recommendation**: Recommended price (EUR/month), confidence range, key factors cited,
  comparable set reference, generated timestamp

## Success Criteria

### Measurable Outcomes

- **SC-001**: Landlords receive a pricing recommendation within 60 seconds of submitting their
  apartment details
- **SC-002**: Pricing recommendations are generated from a minimum of 10 comparable listings when
  available in the configured area
- **SC-003**: A CSV import of 1,000 listings completes processing (validation, deduplication,
  normalization) in under 30 seconds
- **SC-004**: Every pricing recommendation includes a natural language explanation covering at least
  3 distinct market factors
- **SC-005**: 80% of landlords who use the platform rate the pricing recommendation as consistent
  with their own market expectations (validated via in-product feedback prompt)
- **SC-006**: After a CSV upload, the data freshness indicator and listing count update immediately
  without requiring a page reload

## Assumptions

- The platform targets the Berlin rental market exclusively for MVP; multi-city support is out
  of scope
- Listing data is collected **offline** using Fredy (open-source, self-hosted, Docker-based) and
  periodically exported from Fredy's SQLite database as CSV for upload into the platform; Fredy
  is not part of the deployed application architecture
- Fredy is configured to collect from immobilienscout24.de, Immowelt, Immonet, and eBay
  Kleinanzeigen using Berlin-scoped search URLs; additional platforms may be added to Fredy
  without changing the application
- The CSV export schema from Fredy is fixed and documented; the platform's import interface
  is designed against this schema
- Prices are expressed in EUR per month (Warmmiete / warm rent, the Berlin rental standard)
- The platform UI is in English for MVP; German language support is post-MVP
- The primary target device is desktop browser; mobile browser is secondary
- Apartment size is measured in square meters (m²)
- Default comparable filter radius is 2km unless the landlord configures otherwise
- Data upload frequency is at the operator's discretion (e.g., daily or weekly); the platform
  does not enforce an upload schedule
