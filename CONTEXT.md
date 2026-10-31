# OSINT Dashboard

A personal open-source intelligence dashboard that collects public signals (news first, other signal types later) and plots them as Events on an interactive 3D globe.

## Language

### Signals and Events

**Event**:
A single real-world happening shown as one marker on the globe, backed by one or more Sources.
_Avoid_: Story, item, incident, marker (the marker is only its visual)

**Signal Type**:
The kind of feed an Event originates from: News, Earthquake or Hazard (natural disasters such as cyclones, floods, volcanoes, wildfires). Shown as marker shape/icon.
_Avoid_: Feed type, data type, Category

**Ongoing Event**:
An Event that keeps gaining new Sources across several Refreshes; it remains one Event rather than becoming duplicates.
_Avoid_: Developing story, follow-up

**Closed Event**:
An Event with no new Sources for 48 hours; later related Sources start a new Event instead of reopening it.
_Avoid_: Expired, archived, ended

**Significance**:
How important an Event is, from magnitude (Earthquake), alert level (Hazard) or Source count (News). Decides whether an Event is plotted at all and how large its marker is.
_Avoid_: Priority, severity, score, weight

**Summary**:
A short 2–3 sentence description of an Event written by the collector from its Sources' headlines and blurbs, never copied article text.
_Avoid_: Abstract, excerpt, description

**Article**:
One published news piece from one outlet; the Source unit for News Events.
_Avoid_: Story, post, headline

**Source**:
A single piece of evidence attached to an Event (an Article for News).
_Avoid_: Reference, citation

### Classification

**Category**:
The single primary topical bucket of a News Event: Tech, Science or World. Determines marker colour. Non-News Events have no Category.
_Avoid_: Tag, topic, section, Signal Type

### Location

**Location**:
The point on the globe where an Event is plotted.
_Avoid_: Position, coordinates, geo

**Location Basis**:
Why an Event is plotted where it is: either the Event Site (where it happened) or an Organisation HQ (where the main named organisation or institution is based).
_Avoid_: Geo confidence, location type

**Unplaced Event**:
An Event with neither an Event Site nor an Organisation HQ; listed beside the globe but never plotted on it.
_Avoid_: Global event, unknown location

### Time

**Refresh**:
One scheduled collection run, every 6 hours, that brings in new Events.
_Avoid_: Update, sync, scrape

**Snapshot**:
The stored set of Events produced by one Refresh, kept for history.
_Avoid_: Dump, batch, export

**Live Window**:
The rolling 24-hour period of Events shown on the globe by default; older Events fade by age.
_Avoid_: Time range, recent

**Stale**:
The state of the dashboard when the last successful Refresh is more than 7 hours old.
_Avoid_: Outdated, offline

**Last Seen**:
The time of an Event's most recent Source; an Event's age in the Live Window is measured from it.
_Avoid_: Updated at, timestamp
