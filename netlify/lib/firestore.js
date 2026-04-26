// Firestore REST API wrapper — works with Firebase Web API key (no service account needed).
// Reads FIREBASE_API_KEY from env (falls back to FIREBASE_SERVICE_ACCOUNT for legacy var name).

const FIREBASE_API_KEY =
  process.env.FIREBASE_API_KEY || process.env.FIREBASE_SERVICE_ACCOUNT;
const PROJECT_ID = process.env.FIREBASE_PROJECT_ID || 'capital-norvex';
const BASE_URL = `https://firestore.googleapis.com/v1/projects/${PROJECT_ID}/databases/(default)/documents`;

function assertKey() {
  if (!FIREBASE_API_KEY) {
    throw new Error(
      'Firebase API key missing — set FIREBASE_API_KEY (or FIREBASE_SERVICE_ACCOUNT) in Netlify env vars'
    );
  }
}

function toValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === 'boolean') return { booleanValue: v };
  if (typeof v === 'number') {
    return Number.isInteger(v)
      ? { integerValue: String(v) }
      : { doubleValue: v };
  }
  if (typeof v === 'string') return { stringValue: v };
  if (v instanceof Date) return { timestampValue: v.toISOString() };
  if (Array.isArray(v)) {
    return { arrayValue: { values: v.map(toValue) } };
  }
  if (typeof v === 'object') {
    return { mapValue: { fields: toFields(v) } };
  }
  return { stringValue: String(v) };
}

function toFields(obj) {
  const fields = {};
  for (const [k, v] of Object.entries(obj)) {
    fields[k] = toValue(v);
  }
  return fields;
}

function fromValue(v) {
  if (!v) return null;
  if ('nullValue' in v) return null;
  if ('booleanValue' in v) return v.booleanValue;
  if ('integerValue' in v) return parseInt(v.integerValue, 10);
  if ('doubleValue' in v) return v.doubleValue;
  if ('stringValue' in v) return v.stringValue;
  if ('timestampValue' in v) return v.timestampValue;
  if ('arrayValue' in v) return (v.arrayValue.values || []).map(fromValue);
  if ('mapValue' in v) return fromFields(v.mapValue.fields || {});
  return null;
}

function fromFields(fields) {
  const obj = {};
  for (const [k, v] of Object.entries(fields)) {
    obj[k] = fromValue(v);
  }
  return obj;
}

function docIdFromName(name) {
  // name format: projects/{p}/databases/{d}/documents/{collection}/{docId}
  const parts = name.split('/');
  return parts[parts.length - 1];
}

async function getDoc(collection, docId) {
  assertKey();
  const url = `${BASE_URL}/${collection}/${encodeURIComponent(docId)}?key=${FIREBASE_API_KEY}`;
  const resp = await fetch(url);
  if (resp.status === 404) return null;
  if (!resp.ok) {
    throw new Error(`Firestore get(${collection}/${docId}) failed: ${resp.status} ${await resp.text()}`);
  }
  const data = await resp.json();
  const doc = fromFields(data.fields || {});
  doc._id = docIdFromName(data.name);
  return doc;
}

async function listDocs(collection) {
  assertKey();
  const docs = [];
  let pageToken = '';
  do {
    const u = new URL(`${BASE_URL}/${collection}`);
    u.searchParams.set('key', FIREBASE_API_KEY);
    u.searchParams.set('pageSize', '300');
    if (pageToken) u.searchParams.set('pageToken', pageToken);
    const resp = await fetch(u.toString());
    if (!resp.ok) {
      throw new Error(`Firestore list(${collection}) failed: ${resp.status} ${await resp.text()}`);
    }
    const data = await resp.json();
    for (const doc of data.documents || []) {
      const obj = fromFields(doc.fields || {});
      obj._id = docIdFromName(doc.name);
      docs.push(obj);
    }
    pageToken = data.nextPageToken || '';
  } while (pageToken);
  return docs;
}

async function setDoc(collection, docId, data) {
  assertKey();
  const url = `${BASE_URL}/${collection}/${encodeURIComponent(docId)}?key=${FIREBASE_API_KEY}`;
  const resp = await fetch(url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fields: toFields(data) }),
  });
  if (!resp.ok) {
    throw new Error(`Firestore set(${collection}/${docId}) failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

async function updateDoc(collection, docId, partial) {
  assertKey();
  const fields = Object.keys(partial);
  if (fields.length === 0) return;
  const u = new URL(`${BASE_URL}/${collection}/${encodeURIComponent(docId)}`);
  u.searchParams.set('key', FIREBASE_API_KEY);
  for (const f of fields) u.searchParams.append('updateMask.fieldPaths', f);
  const resp = await fetch(u.toString(), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fields: toFields(partial) }),
  });
  if (!resp.ok) {
    throw new Error(`Firestore update(${collection}/${docId}) failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

module.exports = { getDoc, listDocs, setDoc, updateDoc };
