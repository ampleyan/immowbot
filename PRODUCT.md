# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

An individual managing their own Belgian home search. They need to review listings from multiple property portals, decide which ones merit contacting an agent, and keep track of follow-up work.

## Product Purpose

Immowbot is a self-hosted property discovery workspace for finding Belgian listings that fit a buyer's criteria. It reduces the manual effort of checking multiple portals and the noise between finding a listing and deciding whether to contact its agent.

## Positioning

Immowbot combines collection from multiple Belgian portals with buyer-configured hard filters and weighted scoring, translated descriptions, and listing change history in one research and follow-up workspace.

## Operating Context

- The user configures locations, price and property criteria, scoring weights, enabled portals, and collection behavior.
- The user runs collection, reviews passing listings, compares details, and tracks decisions and follow-ups in a listing pipeline.
- The app is self-hosted and accessed through a web interface.
- Listings may be collected from Immoweb, Immoscoop, Zimmo, Realo, and Immovlan. Portal availability and collected details depend on each source.

## Capabilities and Constraints

- Collects listing data from supported Belgian property portals and can run full or delta searches.
- Applies configured hard filters and weighted scores to help prioritize listings.
- Translates Dutch descriptions to English and tracks listing and price changes over time.
- Supports listing review, saved lists, alerts, duplicate handling, comparisons, and follow-up tracking.
- Shows purchase estimates based on user-provided financial assumptions; these are estimates for research, not verified financing or legal advice.
- Contact information availability varies by portal and listing; the app does not guarantee that contact details can be retrieved.

## Brand Commitments

- The product name is Immowbot.
- An existing product icon is available at `frontend/public/immowbot-icon.png`.

## Evidence on Hand

- The repository README documents setup, supported portal sources, search configuration, listing review, and workflow capabilities.
- The frontend contains the implemented web workspace and its listing, alert, list, pipeline, duplicate, history, management, and settings views.
- No testimonials, independently verified performance claims, or third-party endorsements are established in the repository; do not invent them.

## Product Principles

- Help the user spend less time searching and more time evaluating relevant listings.
- Make filters, scores, and estimates understandable enough for the user to exercise judgment.
- Preserve the user's ability to review and decide; recommendations do not make contact or purchasing decisions for them.
- Keep listing research and follow-up work connected so useful context is retained.

