---
name: Immowbot
description: A calm, practical workspace for managing a Belgian home search.
colors:
  vivid-pink: "#E83E8C"
  pink-deep: "#D63384"
  pink-wash: "#FDECF4"
  dark-burgundy: "#4A102A"
  burgundy-deep: "#380C20"
  neutral-bg: "#F2F4F7"
  surface: "#FFFFFF"
  text-primary: "#101828"
  text-secondary: "#667085"
  text-muted: "#98A2B3"
  border: "#E4E7EC"
  dark-bg: "#0F0F0F"
  dark-surface: "#1A1A1A"
  vlaams-gold: "#F5C400"
  score-positive: "#027A48"
  score-warning: "#DC6803"
  score-negative: "#C01048"
typography:
  body:
    fontFamily: "DM Sans, system-ui, -apple-system, sans-serif"
    fontSize: "clamp(13px, 0.85vw, 16px)"
    fontWeight: 400
  label:
    fontFamily: "DM Sans, system-ui, -apple-system, sans-serif"
    fontSize: "0.7rem"
    fontWeight: 600
rounded:
  sm: "4px"
  md: "7px"
  lg: "12px"
  xl: "14px"
  pill: "999px"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
  xl: "1.5rem"
  2xl: "2rem"
components:
  button-primary:
    backgroundColor: "{colors.vivid-pink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "0.35rem 0.85rem"
  property-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "0.55rem 0.875rem"
  filter-chip:
    backgroundColor: "{colors.pink-wash}"
    textColor: "#7A1745"
    rounded: "{rounded.pill}"
    padding: "0.22rem 0.45rem"
---

# Design System: Immowbot

## Overview

**Creative North Star: "The Buyer's Command Desk"**

Immowbot's interface is a compact, practical workspace for managing a property search. A dark burgundy configuration rail holds search criteria and collection controls beside a light, neutral work area for reviewing listings. DM Sans and small, consistent labels keep the dense information legible; vivid pink marks the active path and primary actions.

The overall feel is calm and reassuring, without the stiffness of a generic corporate dashboard. Listing photographs and information remain the focus. The optional Vlaams theme uses near-black surfaces with Flemish gold accents while preserving the same layout and interaction patterns.

**Key Characteristics:**
- Compact, task-oriented information layout
- Dark burgundy controls alongside a light neutral canvas
- Vivid pink accents in the default theme; black and Flemish gold in the optional theme
- Mostly flat surfaces, with restrained elevation for cards and overlays

## Colors

The default theme pairs cool gray work surfaces with a vivid pink accent and a dark burgundy configuration rail; a separate dark theme uses gold for emphasis.

### Primary
- **Vivid Pink** (#E83E8C): Primary buttons, active navigation indicators, focus accents, selected listings, and score-related emphasis.
- **Deep Pink** (#D63384): Hover state for primary actions.
- **Pink Wash** (#FDECF4): Selected filters and soft active states.

### Neutral
- **Cool Canvas** (#F2F4F7): Main application background.
- **White Surface** (#FFFFFF): Cards, navigation, fields, and modal surfaces.
- **Ink** (#101828): Primary text.
- **Slate Text** (#667085): Secondary text, labels, and quiet controls.
- **Muted Slate** (#98A2B3): Tertiary text and subdued metadata.
- **Cool Divider** (#E4E7EC): Surface and section boundaries.
- **Deep Burgundy** (#4A102A): Default sidebar, with a darker burgundy (#380C20) at its lower gradient stop.
- **Score Green** (#027A48): Positive score state.
- **Score Amber** (#DC6803): Caution score state.
- **Score Red** (#C01048): Negative score and alert state.

### Tertiary
- **Vlaams Black** (#0F0F0F): Main background in the optional Vlaams theme.
- **Vlaams Surface** (#1A1A1A): Raised working surfaces in the optional theme.
- **Flemish Gold** (#F5C400): Active and primary emphasis in the optional Vlaams theme.

## Typography

**Display Font:** DM Sans (system sans-serif fallbacks)
**Body Font:** DM Sans (system sans-serif fallbacks)
**Label/Mono Font:** DM Sans; no separate mono face is established.

**Character:** A single sans-serif family supports compact, information-dense reading. Weight and size changes distinguish hierarchy without introducing a display face.

### Hierarchy
- **Headline** (600–700, sizes vary by view): Page titles and primary listing prices.
- **Title** (600, around 1rem): Sidebar product name and section headings.
- **Body** (400, base `clamp(13px, 0.85vw, 16px)`): General interface content.
- **Label** (500–700, commonly 0.68–0.8rem): Form labels, metadata, tabs, and compact controls.

## Layout

The application fills the viewport and uses a two-part shell: a 190px scrollable configuration sidebar and a flexible main column. The main column has a horizontal tab bar and a separately scrolling content area with generous outer padding. The sidebar can collapse to a 48px icon rail. At widths below 720px, navigation and settings adapt to mobile controls, property details use a full-screen drawer, and filter and workflow layouts stack into one column. The interface favors compact repeated spacing from 0.25rem to 1.5rem; property cards use a 14px column gap on desktop.

## Elevation & Depth

The visual system is mostly flat and practical. Borders and background changes define ordinary grouping; subtle shadows lift metric cards and listing cards, while dialogs and drawers receive stronger separation. Hover and selection can deepen a card shadow. The dark theme removes many of these shadows and relies on tonal contrast instead.

### Shadow Vocabulary
- **Card resting** (`0 1px 3px rgba(16,24,40,0.06)`): Light separation for listing cards.
- **Card hover** (`0 4px 14px rgba(16,24,40,0.10)`): Temporary lift while a listing is hovered.
- **Login surface** (`0 10px 30px rgba(176,42,111,0.12)`): Separation for the centered sign-in card.

## Shapes

Controls and surfaces use modest rounded corners, usually 4–12px; login and modal surfaces reach 14px. Filter chips and score badges are fully pill-shaped. Borders define cards, fields, and controls; property photos clip to rounded corners. The mobile property detail drawer becomes edge-to-edge with square corners.

## Components

### Buttons
- **Shape:** Compact rounded rectangle (7px default; 6px small variant).
- **Primary:** Vivid pink fill with white text; standard padding is `0.35rem 0.85rem`.
- **Hover / Focus:** Primary hover darkens to deep pink. Keyboard focus uses a visible pink outline where specified.
- **Secondary / Ghost / Danger:** Secondary buttons use a white fill and gray border; ghost buttons stay transparent until hover; destructive actions use a pale red fill and red text.
- **Sidebar actions:** Primary actions use the same pink; secondary actions use a darker burgundy surface.

### Chips
- **Style:** Filter chips use a pale pink fill, dark wine text, and pill corners.
- **State:** Active status options use the same pale pink and wine pairing; score badges use green, amber, red, or neutral fills with white text.

### Cards / Containers
- **Corner Style:** Listing cards use 12px corners; metric cards use 10px.
- **Background:** White in the default theme; dark gray surfaces in the Vlaams theme.
- **Shadow Strategy:** Subtle at rest and slightly stronger on hover; see Elevation & Depth.
- **Border:** Cool gray at rest, pink or status color for selected and special states.
- **Internal Padding:** Listing rows use about `0.55rem 0.875rem`; metric cards use about `0.875rem 1.25rem`.

### Inputs / Fields
- **Style:** White fields with cool gray borders and 6–8px corners in the main content. Sidebar search fields are transparent with a bottom rule.
- **Focus:** Pink border or underline; some fields add a subtle pink focus ring.
- **Error / Disabled:** Errors use red text and pale red surfaces; disabled actions reduce opacity and use a not-allowed cursor.

### Navigation
- **Style:** White horizontal tab bar with medium-weight DM Sans labels, quiet gray inactive text, and a pink underline for the active tab.
- **Hover / Active:** Hover raises text contrast; active navigation uses ink text and a 2px pink bottom border.
- **Mobile:** A menu control exposes sidebar settings; the tab row remains the main route navigation.

### Property Listing
The signature review unit combines a property photo, score badge, price, address, key specifications, source and status badges, and compact actions. The card expands into detailed review content while keeping selection and workflow state visible.

## Do's and Don'ts

### Do:
- **Do** keep listing information easy to scan in compact, repeated rows.
- **Do** use vivid pink for primary and active states in the default theme.
- **Do** preserve clear contrast between the burgundy configuration rail and the neutral work surface.
- **Do** use score colors consistently: green for positive, amber for caution, red for negative.
- **Do** let property photography and listing facts carry the visual weight.

### Don't:
- **Don't** replace the established DM Sans family with an unrelated display face without a deliberate system change.
- **Don't** use the pink accent as a substitute for score or alert state colors.
- **Don't** add heavy shadows to routine controls and content cards; depth is restrained in the current interface.
- **Don't** turn the dense buyer workspace into a generic marketing dashboard; preserve its practical command-desk character.
