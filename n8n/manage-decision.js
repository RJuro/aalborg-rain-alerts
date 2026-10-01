const request = $('Normalize management request').first().json;
const row = $input.first().json;
const expired = request.action === 'confirm' && (!row.confirmation_requested_at || Date.now() - Date.parse(row.confirmation_requested_at) > 24*3600000);
const valid = request.valid && Number.isInteger(row.id) && (!expired || (row.active === true && row.confirmed === true));
return [{json:{valid,id:row.id ?? -1,active:request.action === 'confirm',confirmed:request.action === 'confirm' ? true : row.confirmed === true,action:request.action},pairedItem:{item:0}}];
