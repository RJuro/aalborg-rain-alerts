const request = $('Validate signup').first().json;
const existing = $input.first().json;
const now = Date.now();
const recentlyRequested = existing.confirmation_requested_at && now - Date.parse(existing.confirmation_requested_at) < 15 * 60000;
const send_confirmation = !(existing.active && existing.confirmed) && !recentlyRequested;
return [{json:{...request,send_confirmation,confirmation_requested_at:new Date(now).toISOString(),subscribed_at:existing.subscribed_at ?? new Date(now).toISOString()},pairedItem:{item:0}}];
