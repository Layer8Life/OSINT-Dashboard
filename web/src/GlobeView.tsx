import { useEffect, useRef } from "react";
import Globe, { type GlobeInstance } from "globe.gl";
import { MeshPhongMaterial } from "three";
import { feature } from "topojson-client";
import type { Topology } from "topojson-specification";
import countriesTopo from "world-atlas/countries-110m.json";
import type { OsintEvent } from "./types";
import { eventColor } from "./theme";
import { ageHours } from "./time";

const RESUME_ROTATE_MS = 20_000;
const RING_MAX_AGE_HOURS = 6;

interface Props {
  events: OsintEvent[]; // placed Events only
  selectedId: string | null;
  windowHours: number;
  now: number;
  onSelect: (id: string) => void;
}

const countries = feature(
  countriesTopo as unknown as Topology,
  (countriesTopo as unknown as Topology).objects.countries,
) as unknown as GeoJSON.FeatureCollection<GeoJSON.Polygon | GeoJSON.MultiPolygon>;

// world-atlas has zero-area slivers (e.g. one of North Korea's polygons) that make H3 throw.
const distinctPoints = (ring: GeoJSON.Position[]) => new Set(ring.map((p) => `${p[0]},${p[1]}`)).size;
for (const f of countries.features) {
  if (f.geometry.type === "MultiPolygon") {
    f.geometry.coordinates = f.geometry.coordinates.filter((poly) => distinctPoints(poly[0]) >= 3);
  }
}

function markerSize(e: OsintEvent): number {
  return Math.round(8 + e.significance * 16);
}

export function GlobeView({ events, selectedId, windowHours, now, onSelect }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeInstance | null>(null);
  const markers = useRef(new Map<string, HTMLDivElement>());
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  // Create the globe once.
  useEffect(() => {
    const host = hostRef.current!;
    const globe = new Globe(host, { animateIn: true })
      .backgroundColor("rgba(0,0,0,0)")
      .globeMaterial(
        new MeshPhongMaterial({ color: "#04101f", emissive: "#020a16", shininess: 8, transparent: true, opacity: 0.96 }),
      )
      .showAtmosphere(true)
      .atmosphereColor("#38bdf8")
      .atmosphereAltitude(0.16)
      .hexPolygonsData(countries.features)
      .hexPolygonResolution(3)
      .hexPolygonMargin(0.45)
      .hexPolygonUseDots(true)
      .hexPolygonColor(() => "rgba(56, 189, 248, 0.55)")
      .htmlLat((d) => (d as OsintEvent).location!.lat)
      .htmlLng((d) => (d as OsintEvent).location!.lon)
      .htmlAltitude(0.005)
      .htmlTransitionDuration(0)
      .htmlElement((d: object) => markers.current.get((d as OsintEvent).id)!)
      .ringLat((d) => (d as OsintEvent).location!.lat)
      .ringLng((d) => (d as OsintEvent).location!.lon)
      .ringColor((d: object) => {
        const c = eventColor(d as OsintEvent);
        return (t: number) => `${c}${Math.round((1 - t) * 255).toString(16).padStart(2, "0")}`;
      })
      .ringMaxRadius((d) => 2 + (d as OsintEvent).significance * 4)
      .ringPropagationSpeed(1.5)
      .ringRepeatPeriod(1800);

    const controls = globe.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
    controls.enableDamping = true;
    let resumeTimer: number | undefined;
    const pause = () => {
      controls.autoRotate = false;
      window.clearTimeout(resumeTimer);
    };
    const scheduleResume = () => {
      window.clearTimeout(resumeTimer);
      resumeTimer = window.setTimeout(() => (controls.autoRotate = true), RESUME_ROTATE_MS);
    };
    controls.addEventListener("start", pause);
    controls.addEventListener("end", scheduleResume);
    globe.pointOfView({ lat: 25, lng: 10, altitude: 2.3 });

    const resize = new ResizeObserver(() => globe.width(host.clientWidth).height(host.clientHeight));
    resize.observe(host);
    globeRef.current = globe;

    return () => {
      resize.disconnect();
      window.clearTimeout(resumeTimer);
      globe._destructor();
      host.innerHTML = "";
      globeRef.current = null;
    };
  }, []);

  // Keep one DOM element per Event and refresh its look.
  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;
    const live = new Set(events.map((e) => e.id));
    for (const id of markers.current.keys()) if (!live.has(id)) markers.current.delete(id);

    for (const e of events) {
      let el = markers.current.get(e.id);
      if (!el) {
        // globe.gl owns the outer element's transform, so the shape lives in a child.
        el = document.createElement("div");
        el.appendChild(document.createElement("div")).className = "marker__shape";
        el.addEventListener("click", (ev) => {
          ev.stopPropagation();
          onSelectRef.current(e.id);
        });
        markers.current.set(e.id, el);
      }
      const fade = Math.min(1, Math.max(0, ageHours(e.last_seen, now) / windowHours));
      el.className = `marker marker--${e.signal_type}${e.id === selectedId ? " marker--selected" : ""}`;
      el.title = e.title;
      el.style.setProperty("--c", eventColor(e));
      el.style.setProperty("--s", `${markerSize(e)}px`);
      el.style.opacity = String(1 - fade * 0.7);
    }
    globe.htmlElementsData(events);
    globe.ringsData(
      events.filter((e) => e.id === selectedId || ageHours(e.last_seen, now) < RING_MAX_AGE_HOURS),
    );
  }, [events, selectedId, windowHours, now]);

  // Fly to the selected Event.
  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;
    if (!selectedId) {
      globe.controls().autoRotate = true;
      return;
    }
    const e = events.find((x) => x.id === selectedId);
    if (!e?.location) return;
    globe.controls().autoRotate = false;
    globe.pointOfView({ lat: e.location.lat, lng: e.location.lon, altitude: 1.4 }, 1200);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  return <div className="globe" ref={hostRef} />;
}
