/* map.js: choropleth map of taxi demand by zone (Leaflet).
 * Data: GET /api/zone-demand -> GeoJSON FeatureCollection; each feature has
 * properties { location_id, zone, borough, pickup_count, dropoff_count }. */
import { getZoneDemand } from "./api.js";

const NYC_CENTER = [40.7128, -74.006];
const COLORS = ["#fff3c4", "#ffe08a", "#ffc83d", "#f5a300", "#d9730d", "#a23e0a", "#5c1f06"]; // light -> dark
const METRICS = {
  pickup_count:  { label: "Pickups",   noun: "pickups" },
  dropoff_count: { label: "Drop-offs", noun: "drop-offs" },
};

let map = null;
let layer = null;
let legend = null;
let features = [];
let metric = "pickup_count";
let breaks = [];

const $ = id => document.getElementById(id);
const fmt = n => Number(n).toLocaleString("en-US");

function setStatus(message) {
  const el = $("map-status");
  if (!el) return;
  el.textContent = message;
  el.hidden = !message;
}

/* ---------- Colour scale (no libraries) ---------- */

// Quantile breaks over the non-zero values, so a few huge zones (airports, Midtown)
// don't turn every other zone the same pale colour. Returns COLORS.length - 1 thresholds.
export function computeBreaks(values, classes = COLORS.length - 1) {
  const sorted = values.filter(v => v > 0).sort((a, b) => a - b);
  if (sorted.length === 0) return [];
  const result = [];
  for (let i = 1; i <= classes; i++) {
    const index = Math.min(Math.floor((i * sorted.length) / (classes + 1)), sorted.length - 1);
    result.push(sorted[index]);
  }
  return result;
}

// Class index for a value: 0 means no trips (drawn grey), 1..n are the colour classes.
export function classOf(value, thresholds) {
  if (!(value > 0)) return 0;
  let cls = 1;
  for (const t of thresholds) {
    if (value >= t) cls += 1;
  }
  return Math.min(cls, COLORS.length);
}

const colorFor = value => (value > 0 ? COLORS[classOf(value, breaks) - 1] : "#e5e8ef");

/* ---------- Layer ---------- */

function styleFeature(feature) {
  return {
    fillColor: colorFor(feature.properties[metric]),
    fillOpacity: 0.8,
    color: "#ffffff",
    weight: 0.8,
  };
}

function tooltipHtml(props) {
  // Zone names come from our own database, but escape anyway: never trust text going into innerHTML.
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  return `<strong>${esc(props.zone)}</strong><br>${esc(props.borough)}<br>` +
         `${fmt(props[metric])} ${METRICS[metric].noun}`;
}

function onEachFeature(feature, featureLayer) {
  featureLayer.bindTooltip(() => tooltipHtml(feature.properties), { sticky: true });
  featureLayer.on({
    mouseover: e => { e.target.setStyle({ weight: 2.5, color: "#14213d" }); e.target.bringToFront(); },
    mouseout:  e => layer.resetStyle(e.target),
  });
}

function drawLegend() {
  if (legend) legend.remove();
  legend = L.control({ position: "bottomright" });
  legend.onAdd = () => {
    const box = L.DomUtil.create("div", "map-legend");
    const title = document.createElement("strong");
    title.textContent = METRICS[metric].label;
    box.appendChild(title);

    const lows = [1, ...breaks];                    // lower bound of each class
    lows.forEach((low, i) => {
      const row = document.createElement("div");
      const swatch = document.createElement("i");
      swatch.style.background = COLORS[i];
      const high = lows[i + 1];
      row.append(swatch, ` ${fmt(low)}${high ? `–${fmt(high - 1)}` : "+"}`);
      box.appendChild(row);
    });
    return box;
  };
  legend.addTo(map);
}

function drawLayer() {
  breaks = computeBreaks(features.map(f => f.properties[metric]));
  if (layer) layer.remove();
  layer = L.geoJSON({ type: "FeatureCollection", features }, { style: styleFeature, onEachFeature }).addTo(map);
  drawLegend();
}

/* ---------- Setup ---------- */

export async function initMap() {
  const container = $("zone-map");
  if (!container) return;

  if (typeof L === "undefined") {
    setStatus("The map library (Leaflet) did not load. Check your internet connection.");
    return;
  }

  map = L.map(container, { zoomControl: true }).setView(NYC_CENTER, 10);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const select = $("map-metric");
  if (select) {
    select.addEventListener("change", () => {
      metric = select.value in METRICS ? select.value : "pickup_count";
      if (features.length) drawLayer();
    });
  }

  setStatus("Loading zone map...");
  try {
    const data = await getZoneDemand();
    features = Array.isArray(data.features) ? data.features : [];
    if (features.length === 0) {
      setStatus("No zone boundaries found. Ask Person 1 to load zone_geometry (build_db.py --shp).");
      return;
    }
    drawLayer();
    map.fitBounds(layer.getBounds(), { padding: [10, 10] });
    setStatus("");
  } catch (err) {
    setStatus(`Could not load the map: ${err.message}`);
  }
}