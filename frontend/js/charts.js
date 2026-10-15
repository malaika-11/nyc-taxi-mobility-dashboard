const COLORS = { accent: "#f5b301", accentSoft: "rgba(245, 179, 1, 0.25)", navy: "#14213d" };

const charts = {};  

export const hourLabel = hour => '${String(hour).padStart(2, "0")}:00';

function pick(row, keys, fallback = undefined) {
    for (const key of keys) {
        if (row[key] !== undefined && row[key] !== null) return row[key]; 
    }
    return fallback;
}

const hourlabel = hour => `${String(hour).padStart(2, "0")}:00`;

function createDemandChart(canvasId, type, labels, values, label, xTitle) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) throw new Error('Chart canvas not found: ${canvasId}');
   if (typeof Chart === "undefined") throw new Error("Chart.js did not load. Check your internet connection.");
   if (values.some(v => !Number.isFinite(v))) {
    throw new Error('Unexpected data format for ${canvasId} (see console)');
   } 
    if (charts[canvasId]) charts[canvasId].destroy();

    const isLine = type === "line";
    charts[canvasId] = new Chart(canvas,{  
        type,
        data: {
            labels,
            datasets: [{
                label,
                data: values,
                backgroundColor: isLine ? COLORS.accentSoft : COLORS.accent,
                borderCOLOR: isLine ? COLORS.navy : COLORS.accent,
                borderWidth: isLine ? 2 : 0,
                borderRadius: isLine ? 0 : 4,
                tension: 0.3,
                fill: isLine,
                pointRadius: isLine ? 2 : 0,
            }],
        },
        options: {
        responsive: true,
        aspectRatio: canvasId === "chart-daily" ? 3 : 1.6,
        interaction: { intersect: false, mode: "index" },
        plugins: {
            legend: { display: true, position: "top" },
            tooltip: { enabled: true },
        },
    scales: {
        x: { title: { display: true, ext: xTitle } },
        y: {
            beginAtZero: true,
            title: { display: true, text: "Number of pickups" },
            ticks: { callback: value => Number(value).toLocaleString() },
        },
    },    
    },    
    });
}

export function renderHourlyChart(rows) {
const sorted = [...rows].sort((a, b) =>
    Number(pick(a, FIELDS.hourly.label, 0)) -
    Number(pick(b, FIELDS.hourly.label, 0))
);

Number(pick(a, FIELDS.hourly.label, 0)) - Number(pick(b, FIELDS.hourly.label, 0));
createDemandChart(
    "chat-hourly", "bar",
    sorted.map(r => hourlabel(Number(pick(r, FIELDS.hourly.label)))),
    sorted.map(r => Number(pick(r, FIELDS.hourly.value))),
    "Taxi pickup", "Hour of day"
);
}

export function normalizeWeekdayRows(rows) {
    const normalized = rows.map(row => {
        const rawDay = pick(row, FIELDS.weekday.label);
        const n = Number(rawDay);
        const dayName = Number.isInteger(n) && n >= 0 && n <= 6 ? WEEKDAYS[n]: String(rawDay);

        const average = pick(row, ["average_daily_pickups", "average_pickups", "count", "trips"]);
        const total = Number(pick(row, ["pickups", "total_pickups", "count", "trips"], 0));
        const numberOfDays = Number(pick(row, ["number_of_days", "days"],0));

        let value;
        if (average !== undefined) value = Number(average);
        else if (numberOfDays > 0) value = total / numberOfDays;
        else value = total;
        
        return { dayName, value };
    });
    normalized.sort((a, b) => WEEKDAYS.indexOf(a.dayName) - WEEKDAYS.indexOf(b.dayName));
    return normalized;
}

export function renderWeekdayChart(rows) {
    const normalized = normalizeWeekdayRows(rows);

    createDemandChart(
        "chart-weekday",
        "bar",
        normalized.map(row => row.dayName),
        normalized.map(row => row.value),
        "Average daily taxi pickups",
        "Day of week"
    );
}

export function renderDailyChart(rows) {
    const sorted = [...rows].sort((a, b) =>
      String(pick(a, FIELDS.daily.label, "")).localeCompare(String(pick(b, FIELDS.daily.label, ""))));
    createDemandChart(
        "chart_daily", "line",
        sorted.map( r=> String(pick(r, FIELDS.daily.label))),
        sorted.map(r => Number(pick(r, FIELDS.daily.value))),
        "Daily taxi pickups", "Date"
 ); 
}