# ADR 0001: Use OpenStreetMap with Leaflet for the map view

## Status

Accepted

## Decision

The listing map view will use Leaflet with OpenStreetMap tiles.

## Context

The first map version needs to show filtered listings beside the existing list, work without a paid API key, and remain easy to run locally.

## Consequences

- The first version has no Mapbox or Google billing/token dependency.
- Tile attribution and usage limits must be respected.
- A future provider can be substituted behind the map component if product needs justify it.
