# Immowbot Buyer Workspace

A property-discovery workspace for quickly identifying Belgian listings worth contacting and reducing review noise.

## Search and listings

**Listing**:
A property found on a supported real-estate portal and stored for review.
_Avoid_: Property result, scrape result

**Passing listing**:
A listing that satisfies the configured hard search filters and receives a score.
_Avoid_: Good listing, accepted property

**Excluded listing**:
A stored listing that fails one or more configured hard filters and is hidden unless explicitly shown.
_Avoid_: Rejected listing, discarded property

**Delta search**:
A collection run that discovers search-result URLs but fetches details only for listings not seen previously.
_Avoid_: Date search, incremental date range

## Map

**Map view**:
A geographic companion to the filtered listing list, showing mappable listings as score-aware markers.
_Avoid_: Location tab, geographic search

**Mappable listing**:
A listing with usable latitude and longitude. Listings without coordinates remain available in the list but do not receive a marker.
_Avoid_: Geocoded listing

**Marker popup**:
A compact summary opened by selecting a map marker; it can open the existing listing detail panel.
_Avoid_: Map card, tooltip
