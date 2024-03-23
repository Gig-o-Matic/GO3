import http from 'k6/http';
import { sleep } from 'k6';
import { parseHTML } from 'k6/html';

const baseurl = 'http://localhost:8000'
// const baseurl = 'https://new.gig-o-matic.com'
const username = ''
const password = ''


export const options = {
  // A number specifying the number of VUs to run concurrently.
  vus: 10,
  // A string specifying the total duration of the test run.
  duration: '30s',
};


// Utility functions inspired by https://k6.io/blog/optimize-your-test-script-with-dsl/
const request = (path, o) => {
  const url = baseurl + path
  const res = http[o.method](url, o.params);
  if (o.connect != null) {
    o.connect(res);
  }
  o.res = res;
  if (o.check != null && !o.check(o) && o.fail != null) {
    o.fail(res);
  } else if (o.ok != null) {
    o.ok(res);
  }
  return res;
};
const get = (path, o = {}) => {
  o.method = 'get';
  return request(path, o);
};
const post = (path, o = {}) => {
  o.method = 'post';
  return request(path, o);
};

const extractCSRFToken = (response) => {
  if (!response || typeof response.html !== 'function') {
    return '';
  }
  let el = response.html().find('input[name=csrfmiddlewaretoken]');
  if (!el) {
    return '';
  }
  el = el.first();
  if (!el) {
    return '';
  }
  return el.attr('value');
};

const randomFromList = (list) => list[Math.floor(Math.random()*list.length)]

const fetchRandomGigDetails = () => {
  // Get the list of gigs without plans
  var r = get('/plans/noplans/1')
  // Also load the gigs marked with plans, to more closely mimic a real client
  get('/plans/plans/1')
  // This URL returns an HTML fragment. Wrap it so it parses correctly
  var doc = parseHTML('<html><body>' + r.body + '</body></html>')
  rsleep()
  // Find only the gig links
  var gig_link = randomFromList(doc.find('a[href^="/gig"]').toArray())
  get(gig_link.attr('href'))
  rsleep()
}

const rsleep = () => sleep(Math.floor(1 + Math.random() * 5));

// Simulate a normal user login flow
// * Request the login page
// * Submit the login form
// * Fetch the agenda page
// * Repeat 3 times:
//   * Fetch the gig plans
//   * Select a random gig and view its details
export default function() {
  var r
  r = get('')
  rsleep()
  var csrftoken = extractCSRFToken(r)
  post('/accounts/login/', {params: {csrfmiddlewaretoken: csrftoken, username: username, password: password}})
  fetchRandomGigDetails()
  fetchRandomGigDetails()
  fetchRandomGigDetails()
}
