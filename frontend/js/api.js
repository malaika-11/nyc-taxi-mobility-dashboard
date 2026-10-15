export const API_BASE = "http://127.0.0.1:5000"
export function buildQuery (params = {}) {
    const query = new URLSearchParams()
    for  (const[key, value] of Object.entries(params)) {
        if (value !=="" && value !== null && value !== undefined) {
            query.append(key, value)
        }
    }
    const text = query.toString()
    return text ? '?${text}' : "" ;
}

export async function getJSON(path, params = {} ) {
    let response;
    try {
        response = await fetch(`${API_BASE}${path}${buildQuery(params)}`);
    } catch (networkError) {
        throw new Error("Cannot reach the server. Is the backend running?")
    }
    if (!response.ok) {
        throw new Error ('Server returned ${response.status} for ${path}')
    }
    try {
        return await response.json(); 
    } catch (parseError) {
        throw new Error('Server sent invalid JSON for ${path}')
    }
}

export const getHealth         =()        => getJSON("/api/health");
export const getSummary        =()        => getJSON("/api/summary");
export const getHourlyDemand   =()        => getJSON("/api/hourly-demand");
export const getWeekdayAvg     =()        => getJSON("/api/weekly-average");
export const getDailyDemand    =()        => getJSON("/api/daily-demand");
export const getZones          =()        => getJSON("api/zones");
export const getTrips          =(filters) => getJSON("/api/trips", filters);
export const getTripDetail     =(id)      => getJSON('/api/trips/${id}');
