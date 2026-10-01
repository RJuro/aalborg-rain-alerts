const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const now = Date.parse('2026-10-01T10:30:00Z');
class Clock extends Date { constructor(...args){super(...(args.length ? args : [now]));} static now(){return now;} }
function run(file, input, sources = {}) {
  return new vm.Script('(function(){' + fs.readFileSync('n8n/' + file,'utf8') + '})()').runInNewContext({
    Date:Clock,
    $input:{first:()=>({json:input})},
    $:name=>({first:()=>({json:sources[name]})}),
  })[0].json;
}
function rawForecast(){
  return {hourly:{
    time:Array.from({length:26},(_,i)=>Date.parse('2026-10-01T10:00:00Z')/1000+i*3600),
    precipitation_probability:Array(26).fill(0),rain:Array(26).fill(0),
    showers:Array(26).fill(0),temperature_2m:Array(26).fill(12)
  },current:{temperature_2m:12}};
}
let data = rawForecast();
assert.equal(run('weather-normalizer.js',data).rain_likely,false);
data.hourly.precipitation_probability[2]=60;
data.hourly.rain[2]=0.2;
let weather=run('weather-normalizer.js',data);
assert.equal(weather.rain_likely,true);
assert.equal(weather.first_rain_start,'2026-10-01T11:00:00.000Z');
assert.equal(weather.hours.length,24);
data.hourly.precipitation_probability[2]=59;
assert.equal(run('weather-normalizer.js',data).rain_likely,false);
data.hourly.precipitation_probability[2]=99; data.hourly.rain[2]=0.1;
assert.equal(run('weather-normalizer.js',data).rain_likely,false);
data.hourly.showers[2]=0.1;
assert.equal(run('weather-normalizer.js',data).rain_likely,true);
data = rawForecast();data.hourly.precipitation_probability[10]=99; data.hourly.rain[10]=5;
assert.equal(run('weather-normalizer.js',data).rain_likely,false);
data.hourly.precipitation_probability[1]=null;
assert.throws(()=>run('weather-normalizer.js',data),/unavailable/);
const body={email:' Student+test@EXAMPLE.com ',consent:true,confirm_token:'a'.repeat(43),unsubscribe_token:'b'.repeat(43)};
assert.equal(run('signup-validation.js',{body}).valid,true);
assert.equal(run('signup-validation.js',{body}).email,'student+test@example.com');
assert.equal(run('signup-validation.js',{body:{...body,email:'a@example.com,b@example.com'}}).valid,false);
assert.equal(run('signup-validation.js',{body:{...body,consent:false}}).valid,false);
assert.equal(run('signup-validation.js',{body:{...body,confirm_token:body.unsubscribe_token}}).valid,false);
const request=run('signup-validation.js',{body});
assert.equal(run('signup-decision.js',{}, {'Validate signup':request}).send_confirmation,true);
assert.equal(run('signup-decision.js',{active:true,confirmed:true}, {'Validate signup':request}).send_confirmation,false);
assert.equal(run('signup-decision.js',{confirmation_requested_at:new Date(now-60000).toISOString()}, {'Validate signup':request}).send_confirmation,false);
assert.equal(run('signup-decision.js',{confirmation_requested_at:new Date(now-16*60000).toISOString()}, {'Validate signup':request}).send_confirmation,true);
const management={valid:true,action:'confirm'};
assert.equal(run('manage-decision.js',{id:1,confirmation_requested_at:new Date(now-1000).toISOString()},{'Normalize management request':management}).valid,true);
assert.equal(run('manage-decision.js',{id:1,confirmation_requested_at:new Date(now-25*3600000).toISOString()},{'Normalize management request':management}).valid,false);
assert.equal(run('manage-decision.js',{}, {'Normalize management request':management}).valid,false);
const unsub=run('manage-decision.js',{id:1,active:true,confirmed:true},{'Normalize management request':{valid:true,action:'unsubscribe'}});
assert.equal(unsub.valid,true);assert.equal(unsub.active,false);assert.equal(unsub.confirmed,true);
console.log('Workflow logic: 21 assertions passed (thresholds, timing, validation, duplicate prevention, confirmation and opt-out).');
