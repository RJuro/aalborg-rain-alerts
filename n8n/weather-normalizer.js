const source = $input.first().json;
const hourly = source.hourly;
const nowMs = Date.now();
const horizonMs = nowMs + 6 * 3600000;
const fields = ['time', 'precipitation_probability', 'rain', 'showers', 'temperature_2m'];
if (!hourly || fields.some(key => !Array.isArray(hourly[key]))) throw new Error('Incomplete forecast from Open-Meteo');
const hours = hourly.time.map((time, i) => {
  const endMs = Number(time) * 1000;
  const probability = hourly.precipitation_probability[i];
  const rain = hourly.rain[i];
  const showers = hourly.showers[i];
  return {
    start: new Date(endMs - 3600000).toISOString(),
    end: new Date(endMs).toISOString(),
    probability: typeof probability === 'number' ? probability : null,
    rain_mm: typeof rain === 'number' && typeof showers === 'number' ? Number((rain + showers).toFixed(2)) : null,
    temperature_c: hourly.temperature_2m[i] ?? null
  };
}).filter(h => Date.parse(h.end) > nowMs).slice(0, 24);
const window = hours.filter(h => Date.parse(h.start) < horizonMs);
if (!window.length || window.some(h => h.probability === null || h.rain_mm === null)) throw new Error('Forecast unavailable in the alert window');
const wet = window.filter(h => h.probability >= 60 && h.rain_mm >= 0.2);
return [{ json: {
  city: 'Aalborg', latitude: 57.048, longitude: 9.919, timezone: 'Europe/Copenhagen',
  fetched_at: new Date(nowMs).toISOString(), provider: 'Open-Meteo',
  threshold_percent: 60, minimum_rain_mm: 0.2, horizon_hours: 6, cooldown_hours: 6,
  rain_likely: wet.length > 0, first_rain_start: wet[0]?.start ?? null,
  first_rain_end: wet[0]?.end ?? null,
  max_hourly_probability: Math.max(...window.map(h => h.probability)),
  expected_rain_mm: Number(window.reduce((sum, h) => sum + h.rain_mm, 0).toFixed(2)),
  current_temperature_c: source.current?.temperature_2m ?? null,
  current_wind_kmh: source.current?.wind_speed_10m ?? null,
  hours
}, pairedItem: {item: 0} }];
