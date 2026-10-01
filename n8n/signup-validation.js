const body = $input.first().json.body ?? {};
const email = typeof body.email === 'string' ? body.email.trim().toLowerCase() : '';
const tokenOK = value => typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value);
const valid = email.length <= 254 && /^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$/i.test(email) && body.consent === true && tokenOK(body.confirm_token) && tokenOK(body.unsubscribe_token) && body.confirm_token !== body.unsubscribe_token;
return [{json:{valid,email,confirm_token:body.confirm_token,unsubscribe_token:body.unsubscribe_token},pairedItem:{item:0}}];
