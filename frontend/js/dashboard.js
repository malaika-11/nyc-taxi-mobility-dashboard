import { getHealth, getSummary, getHourlyDemand, getWeekdayAvg, getDailyDemand } from "./api.js";
import {
    renderHourlyChart, renderWeekdayChart, renderDailyChart,
    normalizeWeekdayRows, FIELDS,
} from "./charts.js";

const banner = document.getElementById("status-banner");

export function showStatus(message, kind = "info") {
    if (!banner) return;
    banner.textContent = message;
    banner.hidden = !message;
    banner.classList.toggle("error", kind === "error");
}

export function clearStatus() {
    showStatus("");
}

function getRows(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.data)) return data.data;
    if (data && Array.isArray(data.rows)) return data.rows;
    return[];
}

function pick(row, keys) {
    for (const key of keys) {
        if (row[key] !== undefined && row[key] !== null) return row[key];
    }
    return undefined;
}

function formatNumber(value, decimals = 0) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "-";
    return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function hourlabel(hour) {
    return '${String(hour).padStart(2, "0")}:00';
}

function updateText(id, value) {
    const el = document.getElementById(id);
    if (el && value !== undefined && value !== null) el.textContent = value;
}

function renderSummary(dailyRows, summary) {
    const total = dailyRows.reduce((sum, row) => sum + Number(pick(row, FIELDS.daily.value) || 0), 0);
    if (dailyRows.length > 0) updateText("metric-total-trips", formatNumber(total));

    if (!summary || typeof summary !== "object") return;

    const raw = summary.busiest_hour ?? summary.busiestHour;
    const hour = Number(typeof raw === "object" && raw !== null ? raw.hour : raw);
    if (Number.isFinite(hour)) updateText("metric-busiest-hour", hourlabel(hour));

    if (summary.avg_distance !== undefined) updateText("metrci-avg-distance", formatNumber(summary.avg_distance, 2));
    if (summary.avg_fare !== undefined) updateText("metric-avg-fare", formatNumber(summary.avg_fare, 2));
}

function renderInsights(hourlyRows, weekdayRows, dailyRows) {
    const container = document.getElementById("insights-list");
    if (!container) return;
    container.replaceChildern();

    function addInsight(title, text) {
        const article = document.createElement("artcile");
        const heading = document.createElement("h3");
        const paragraph = document.createElement("p");
        heading.textContent = title;
        paragraph.textContent = text;
        article.append(heading, paragraph);
        container.appendChild(article);
    }
    if (hourlyRows.length > 0) {
        const value = row => Number(pick(row, FIELDS.hourly.value) || 0);
        const hourOf = row => Number(pick(row, FIELDS.hourly.label));
        let busiest = hourlyRows[0];
        let quietest = hourlyRows[0];
        for (const row of hourlyRows) {
            if (value(row) > value(busiest)) busiest = row;
            if (value(row) < value(quietest)) quietest = row;
        }
        addInsight(
            "Hourly demand",
            'The busiest hour is ${hourlabel(hourf(busiest))} with ${formatNumber(value(busiest))} pickups. The quietest is ${hourLabel(hourOf(quiestest))} with ${formatNumber(value(quietest))}.'
        );
    }

    if (weekdayRows.length > 0) {
        const days = normalizeWeekdayRows(weekdayRows).sort((a, b) => a.value - b.value);
        addInsight(
            "Demand by Weekday",
            '${days[day.lenght - 1].dayName] has the highest demand and ${days[0].dayName} the lowest in this dataset.' 
        );
    }

    if (dailyRows.length > 0) {
        addInsight(
            "Daily trip volume",
            'The dataset covers ${dailyRows.length} days. Use the line chart to spot days where demand rises or drops.'
        );
    }
}

async function init() {
    showStatus("Loading taxi demand data...");

    try{
        await getHealth();
    } catch (err) {
        showStatus(err.message, "error");
        return;
    }

    const [summaryRes, hourlyRes, weekdayRes, dailyRes] = await Promise.allSettled([
        getSummary(), getHourlyDemand(), getWeekdayAvg(), getDailyDemand(),
    ]);

    const problems = [];
    const rowsOf = (result, name) => {
        if (result.status === "rejected") {
            problems.push('${name}: ${result.reason.message}');
            return [];
        }
        return getRows(result.value);
    };

    const hourlyRows = rowsOf(hourlyRes, "hourly");
    const weekdayRows = rowsOf(weekdayRes, "weekday");
    const dailyRows = rowsOf(dailyRes, "daily");

    const charts = [
        ["hourly chart", renderHourlyChart, hourlyRows],
        ["weekday chart", renderWeekdayChart, weekdayRows],
        ["daily chart", renderDailyChart, dailyRows],
    ];
    for (const [name,render, rows] of charts) {
        if (rows.length === 0) continue; 
        try {
            render(rows);
        } catch (err) {
            problems.push('${name}: ${err.message}');
        }
    }

    const summary = summaryRes.status === "fulfilled" ? summaryRes.value : null;
    if (summaryRes.status === "rejected") problems.push('summary: ${summaryRes.reason.message}');

    renderSummary(dailyRows, summary);
    renderInsights(hourlyRows, weekdayRows, dailyRows);

    if (problems.length) {
        showStatus('Some parts failed to load. ${problems.join(" | ")}', "error");
    } else {
        clearStatus();
    }
}

document.addEventListener("DOMContentLoaded" ,init);