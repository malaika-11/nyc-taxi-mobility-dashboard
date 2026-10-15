import { getHealth, getSummary, getHourlyDemand, getWeekdayAverage, getDailyDemand, getBoroughs, getTrips, getTripDetail,} from "./api.js";

import { renderHourlyChart, renderWeekdayChart, renderDailyChart,normalizeWeekdayRows, FIELDS,} from "./charts.js";

const PAGE_SIZE = 25;
const state = { page: 1, totalPages: 1 };

const $ = id => document.getElementById(id);
const banner = $("status-banner");

export function showStatus(message, kind = "info") {
    if (!banner) return;
    banner.textContent = message;
    banner.hidden = !message;
    banner.classList.toggle("error", kind === "error");
}

export const clearStatus = () => showStatus("");

function formatNumber(value, decimals = 0) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "-";
    return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

const money = value => (Number.isFinite(Number(value)) ? "$" + formatNumber(value, 2) : "-");
const setText = (id, value) => { const el = $(id); if (el) el.textContent = value; };

function renderSummary(summary) {
    setText("metric-total-trips", formatNumber(summary.total_pickups));
    setText("metric-average-distance", formatNumber(summary.avg_distance, 2));
    setText("metric-average-fare", formatNumber(summary.avg_fare, 2));
    setText("metric-busiest-hour", hourLabel(summary.busiest_hour));
}

function renderInsights(summary, weekdayRows, dailyRows) {
    const container = $("insight-list");
    container.replaceChildren();
    const add = (title, text) => {
        const article = document.createElement("article");
        const heading = document.createElement("h3");
        const paragraph = document.createElement("p");
        heading.textContent = title;
        paragraph.textContent = text;
        article.append(heading, paragraph);
        container.appendChild(article);
    };

    add("Hourly demand",
        `The busiest hour is ${hourLabel(summary.busiest_hour)} with ${formatNumber(summary.busiest_hour_count)} pickups. ` +
        `The quietest is ${hourLabel(summary.quietest_hour)} with ${formatNumber(summary.quietest_hour_count)}.`);

    if (weekdayRows.length) {
        const byAverage = [...weekdayRows].sort((a, b) => a.average_pickups - b.average_pickups);
        const low = byAverage[0], high = byAverage[byAverage.length - 1];
        add("Demand by weekday",
            `${high.day_of_week} has the highest average daily demand (${formatNumber(high.average_pickups)} pickups per day) ` +
            `and ${low.day_of_week} the lowest (${formatNumber(low.average_pickups)}).`);
    }

    if (dailyRows.length) {
        const sorted = [...dailyRows].sort((a, b) => a.pickup_count - b.pickup_count);
        const low = sorted[0], high = sorted[sorted.length - 1];
        add("Daily trip volume",
            `Across ${dailyRows.length} days, ${high.date} was busiest (${formatNumber(high.pickup_count)} trips) ` +
            `and ${low.date} quietest (${formatNumber(low.pickup_count)}).`);
    }
}

function readFilters() {
    return {
        start_date: $("filter-from-date").value,
        end_date: $("filter-to-date").value,
        min_distance: $("filter-min-distance").value,
        max_distance: $("filter-max-distance").value,
        min_fare: $("filter-min-fare").value,
        max_fare: $("filter-max-fare").value,
        pickup_borough: $("filter-pu-borough").value,
        dropoff_borough: $("filter-do-borough").value,
        sort_by: $("filter-sort").value,
        sort_order: $("filter-order").value,
    };
}

function validateFilters(f) {
    const pairs = [
        ["start_date", "end_date", "The 'From' date must be before the 'To' date."],
        ["min_distance", "max_distance", "Minimum distance cannot be larger than maximum distance."],
        ["min_fare", "max_fare", "Minimum fare cannot be larger than maximum fare."],
    ];
    for (const [low, high, message] of pairs) {
        if (f[low] !== "" && f[high] !== "") {
            const a = low.endsWith("date") ? f[low] : Number(f[low]);
            const b = high.endsWith("date") ? f[high] : Number(f[high]);
            if (a > b) return message;
        }
    }
    for (const key of ["min_distance", "max_distance", "min_fare", "max_fare"]) {
        if (f[key] !== "" && Number(f[key]) < 0) return "Distance and fare filters cannot be negative.";
    }
    return "";
}

function cell(row, text) {
    const td = document.createElement("td");
    td.textContent = text;
    row.appendChild(td);
}

async function loadTrips() {
    const filters = readFilters();
    const error = $("filter-error");
    const problem = validateFilters(filters);
    error.textContent = problem;
    error.hidden = !problem;
    if (problem) return;

    const body = $("trips-body");
    $("page-info").textContent = "Loading...";
    try {
        const result = await getTrips({ ...filters, page: state.page, limit: PAGE_SIZE });
        state.totalPages = Math.max(result.total_pages, 1);
        body.replaceChildren();

        if (result.data.length === 0) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");
            td.colSpan = 6;
            td.textContent = "No trips match these filters.";
            tr.appendChild(td);
            body.appendChild(tr);
        }
        for (const trip of result.data) {
            const tr = document.createElement("tr");
            tr.title = "Click for trip details";
            cell(tr, trip.pickup_datetime);
            cell(tr, `${trip.pu_zone} (${trip.pu_borough})`);
            cell(tr, `${trip.do_zone} (${trip.do_borough})`);
            cell(tr, formatNumber(trip.trip_distance, 2));
            cell(tr, money(trip.fare_amount));
            cell(tr, money(trip.total_amount));
            tr.addEventListener("click", () => openDetail(trip.trip_id));
            body.appendChild(tr);
        }
        $("page-info").textContent =
            `Page ${formatNumber(result.page)} of ${formatNumber(state.totalPages)} (${formatNumber(result.total)} trips)`;
        $("prev-page").disabled = state.page <= 1;
        $("next-page").disabled = state.page >= state.totalPages;
        clearStatus();
    } catch (err) {
        $("page-info").textContent = "-";
        showStatus("Could not load trips: " + err.message, "error");
    }
}

function applyFilters() { state.page = 1; loadTrips(); }

function resetFilters() {
    for (const id of ["filter-from-date", "filter-to-date", "filter-min-distance", "filter-max-distance",
                      "filter-min-fare", "filter-max-fare", "filter-pu-borough", "filter-do-borough"]) {
        $(id).value = "";
    }
    $("filter-sort").value = "date";
    $("filter-order").value = "desc";
    applyFilters();
}

async function openDetail(tripId) {
    const panel = $("trip-detail");
    const content = $("trip-detail-content");
    content.textContent = "Loading...";
    panel.hidden = false;
    try {
        const t = await getTripDetail(tripId);
        const rows = [
            ["Trip ID", t.trip_id],
            ["Pickup", `${t.pickup_datetime} - ${t.pu_zone}, ${t.pu_borough}`],
            ["Dropoff", `${t.dropoff_datetime} - ${t.do_zone}, ${t.do_borough}`],
            ["Distance", formatNumber(t.trip_distance, 2) + " mi"],
            ["Duration", formatNumber(t.duration_min, 1) + " min"],
            ["Average speed", formatNumber(t.avg_speed_mph, 1) + " mph"],
            ["Passengers", t.passenger_count ?? "-"],
            ["Vendor", t.vendor],
            ["Rate code", t.rate_code],
            ["Payment", t.payment_type],
            ["Metered fare", money(t.fare_amount)],
            ["Extra / MTA tax", `${money(t.extra)} / ${money(t.mta_tax)}`],
            ["Tolls", money(t.tolls_amount)],
            ["Surcharges", money((t.improvement_surcharge || 0) + (t.congestion_surcharge || 0) + (t.airport_fee || 0) + (t.cbd_congestion_fee || 0))],
            ["Tip", `${money(t.tip_amount)}${t.tip_pct != null ? ` (${formatNumber(t.tip_pct, 1)}% of fare)` : ""}`],
            ["Total", money(t.total_amount)],
            ["Fare per mile", t.fare_per_mile != null ? money(t.fare_per_mile) : "-"],
        ];
        const list = document.createElement("dl");
        for (const [label, value] of rows) {
            const dt = document.createElement("dt");
            const dd = document.createElement("dd");
            dt.textContent = label;
            dd.textContent = String(value);
            list.append(dt, dd);
        }
        const title = document.createElement("h2");
        title.textContent = "Trip details";
        content.replaceChildren(title, list);
    } catch (err) {
        content.textContent = "Could not load trip: " + err.message;
    }
}

async function fillBoroughs() {
    try {
        const names = await getBoroughs();
        for (const id of ["filter-pu-borough", "filter-do-borough"]) {
            for (const name of names) {
                const option = document.createElement("option");
                option.value = option.textContent = name;
                $(id).appendChild(option);
            }
        }
    } catch (err) {
        showStatus("Could not load borough list: " + err.message, "error");
    }
}

async function init() {
    showStatus("Loading taxi demand data...");

    try {
        await getHealth();
    } catch (err) {
        showStatus(err.message, "error");
        return;
    }

    $("filter-apply").addEventListener("click", applyFilters);
    $("reset-filters").addEventListener("click", resetFilters);
    $("prev-page").addEventListener("click", () => { if (state.page > 1) { state.page--; loadTrips(); } });
    $("next-page").addEventListener("click", () => { if (state.page < state.totalPages) { state.page++; loadTrips(); } });
    $("close-detail").addEventListener("click", () => { $("trip-detail").hidden = true; });
    document.addEventListener("keydown", e => { if (e.key === "Escape") $("trip-detail").hidden = true; });

    const [summaryRes, hourlyRes, weekdayRes, dailyRes] = await Promise.allSettled([
        getSummary(), getHourlyDemand(), getWeekdayAverage(), getDailyDemand(),

    ]);

    const problems = [];
    const valueOf = (result, name, fallback) => {
        if (result.status === "rejected") {
            problems.push(`${name}: ${result.reason.message}`);
            return fallback;
        }
        return result.value;
    };
    const summary = valueOf(summaryRes, "summary", null);
    const hourlyRows = valueOf(hourlyRes, "hourly", []);
    const weekdayRows = valueOf(weekdayRes, "weekday", []);
    const dailyRows = valueOf(dailyRes, "daily", []);

    for (const [name, render, rows] of [
        ["hourly chart", renderHourlyChart, hourlyRows],
        ["weekday chart", renderWeekdayChart, weekdayRows],
        ["daily chart", renderDailyChart, dailyRows],

    ]) {
        if (!rows.length) continue;
        try { render(rows); } catch (err) { problems.push(`${name}: ${err.message}`); }
    }

    if (summary) {
        renderSummary(summary);
        renderInsights(summary, weekdayRows, dailyRows);
    }

    await fillBoroughs();
    await loadTrips();

    if (problems.length) {
        showStatus(`Some parts failed to load. ${problems.join(" | ")}`, "error");
    }
}

document.addEventListener("DOMContentLoaded", init);
