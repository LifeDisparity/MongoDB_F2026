/** Browser → FastAPI → real MongoDB engineering E2E. No model/Atlas pass implied. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'frontend/package.json'));
const { chromium } = require('playwright');
const stamp = new Date().toISOString().replaceAll(':', '-');
const artifactDir = path.join(root, 'artifacts/private', 'workspace-' + stamp);
await mkdir(artifactDir, { recursive: true });
const startedAt = Date.now();
const database = 'living_atlas_e2e_' + Date.now();
const apiPort = process.env.E2E_API_PORT || '8001';
const webPort = process.env.E2E_WEB_PORT || '5174';
const apiUrl = 'http://127.0.0.1:' + apiPort;
const webUrl = 'http://127.0.0.1:' + webPort;
const env = {
  ...process.env,
  MONGODB_URI: process.env.MONGODB_URI || 'mongodb://127.0.0.1:27019/?replicaSet=living-atlas-dev',
  MONGODB_DATABASE: database,
  ENABLE_DEMO_SOURCE_WITHDRAWAL: 'true',
  // This engineering run must not consume provider credentials or imply inference.
  OPENAI_API_KEY: '',
  MODEL_ID: '',
  API_TARGET: apiUrl,
};
const services = [];
const logs = [];
function start(command, args, cwd = root) {
  const child = spawn(command, args, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'], detached: true });
  child.stdout.on('data', data => logs.push(data.toString()));
  child.stderr.on('data', data => logs.push(data.toString()));
  services.push(child);
  return child;
}
function stop(child, signal = 'SIGTERM') {
  if (child && child.exitCode === null && child.signalCode === null) {
    try { process.kill(-child.pid, signal); } catch (error) { if (error.code !== 'ESRCH') throw error; }
  }
}
async function ready(url) {
  for (let n = 0; n < 120; n++) {
    try { if ((await fetch(url)).ok) return; } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Service did not become ready: ' + url);
}
async function json(route, options) {
  const response = await fetch(apiUrl + route, options);
  const body = await response.json();
  assert(response.ok, JSON.stringify({ route, status: response.status, body }));
  return body;
}
function post(body) {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}
const checks = [];
let browser;
let apiProcess;
const startApi = () => start(path.join(root, '.venv/bin/python'),
  ['-m', 'uvicorn', 'living_atlas.api.app:app', '--host', '127.0.0.1', '--port', apiPort]);
try {
  apiProcess = startApi();
  start(process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', webPort, '--strictPort'], path.join(root, 'frontend'));
  await Promise.all([ready(apiUrl + '/health'), ready(webUrl)]);
  const health = await json('/health');
  assert.deepEqual(health.model_adapter, { configured: false, model_id: null, error_code: 'model_not_configured' });
  assert.equal(health.scientific_workflow, 'not_configured');
  checks.push('Health distinguishes an unconfigured model adapter from the unimplemented scientific workflow');
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(webUrl);
  await page.getByRole('button', { name: /Explore dependency demo/ }).click();
  await page.getByText('Synthetic engineering fixture', { exact: true }).first().waitFor();
  await page.getByRole('heading', { name: 'The atlas, in context.' }).waitFor();
  const runId = new URL(page.url()).searchParams.get('run');
  assert(runId, 'UI did not retain the created run ID');
  const initial = await json('/runs/' + runId + '/snapshot');
  assert.equal(initial.claims.length, 3);
  assert.equal(initial.last_sequence, 1);
  assert(initial.claims.every(claim => claim.status === 'supported'));
  checks.push('Browser created labeled fixture in real MongoDB');
  await page.waitForFunction(() => {
    const canvas = document.querySelector('.graph-canvas')?.getBoundingClientRect();
    const nodes = [...document.querySelectorAll('.react-flow__node')];
    return canvas && nodes.length === 8 && nodes.every(node => {
      const box = node.getBoundingClientRect();
      return box.top >= canvas.top - 1 && box.bottom <= canvas.bottom + 1 &&
        box.left >= canvas.left - 1 && box.right <= canvas.right + 1;
    });
  });
  checks.push('All graph nodes fit within the canvas at 1440×900');
  await page.getByRole('button', { name: 'New run', exact: true }).click();
  for (let n = 0; n < 9; n++) {
    await page.keyboard.press('Tab');
    assert(await page.evaluate(() => document.querySelector('dialog')?.contains(document.activeElement)), 'Modal focus escaped');
  }
  await page.keyboard.press('Escape');
  assert(await page.getByRole('button', { name: 'New run', exact: true }).evaluate(node => node === document.activeElement));
  await page.getByRole('button', { name: /Inspect claim A:/ }).press('Enter');
  await page.getByText('Canonical source passage', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Close inspector selection' }).click();
  checks.push('Modal traps keyboard focus, Escape restores its opener, and graph claims open with Enter');
  await page.screenshot({ path: path.join(artifactDir, '01-initial.png'), fullPage: true });

  await page.getByRole('button', { name: /S1.*Synthetic engineering source/ }).last().click();
  await page.getByRole('button', { name: 'Simulate source withdrawal' }).click();
  await page.getByText('1 require review', { exact: true }).waitFor();
  const withdrawn = await json('/runs/' + runId + '/snapshot');
  const claim = id => withdrawn.claims.find(row => row.claim_id === id);
  assert.equal(claim('A').status, 'unsupported');
  assert.equal(claim('B').status, 'supported');
  assert.deepEqual(claim('B').usable_evidence_ids, ['E2']);
  assert.deepEqual(claim('C'), initial.claims.find(row => row.claim_id === 'C'));
  assert.equal((await json('/runs/' + runId + '/evidence/E1')).available, false);
  checks.push('Source withdrawal: A loses sole support; B retains S2; C unchanged; old evidence inspectable');
  await page.screenshot({ path: path.join(artifactDir, '02-withdrawn.png'), fullPage: true });

  // Repeat the exact accepted request through HTTP, then reject an ID collision.
  const events = [];
  let cursor = 0;
  while (true) {
    const next = await json('/runs/' + runId + '/events?after=' + cursor + '&limit=1');
    events.push(...next.events);
    cursor = next.events.at(-1)?.sequence ?? cursor;
    if (!next.has_more) break;
  }
  assert.equal(events.length, withdrawn.last_sequence);
  const changed = events.find(event => event.type === 'source.availability_changed');
  const history = changed.payload.availability_history.at(-1);
  const duplicateBody = {
    source_id: 'S1', source_version: changed.payload.source_version, available: false,
    operation_id: changed.operation_id, reason: history.reason,
  };
  const duplicate = await json('/runs/' + runId + '/demo-events/source-withdrawal', post(duplicateBody));
  assert.equal(duplicate.replayed, true);
  const collision = await fetch(apiUrl + '/runs/' + runId + '/demo-events/source-withdrawal', post({ ...duplicateBody, available: true }));
  assert.equal(collision.status, 409);
  checks.push('Accepted operation retry deduplicates; changed payload under same ID rejects');

  const slider = page.getByRole('slider', { name: 'Replay event' });
  await slider.focus();
  await slider.press('Home');
  await slider.press('ArrowRight');
  await page.getByText('3 supported', { exact: true }).waitFor();
  assert(await page.getByRole('link', { name: 'Export live dossier', exact: true }).isVisible());
  assert(await page.getByRole('button', { name: 'Simulate source withdrawal' }).isDisabled());
  await page.getByRole('button', { name: 'Return to live' }).click();
  await page.getByText('1 require review', { exact: true }).waitFor();
  checks.push('Browser replay restores initial support and disables writes; return to live restores withdrawn state');

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Export dossier' }).click();
  const download = await downloadPromise;
  const exportPath = path.join(artifactDir, 'dossier.json');
  await download.saveAs(exportPath);
  assert.deepEqual(JSON.parse(await readFile(exportPath, 'utf8')), withdrawn);
  checks.push('Downloaded dossier independently matches current snapshot without article text');

  stop(apiProcess, 'SIGKILL');
  await new Promise(resolve => apiProcess.once('exit', resolve));
  apiProcess = startApi();
  await ready(apiUrl + '/health');
  await page.reload();
  await page.getByText('1 require review', { exact: true }).waitFor();
  assert.deepEqual(await json('/runs/' + runId + '/snapshot'), withdrawn);
  checks.push('Actual API process SIGKILL/restart retains accepted state and browser reconnects (not workflow recovery)');

  // Duplicate deliveries use the actual UI reducer, bundled by Vite.
  const parity = await page.evaluate(async ({ events, expected }) => {
    const module = await import('/src/replay/events.ts');
    const partial = module.appendEvents([], [events[0], events.at(-1)]);
    const recovered = module.appendEvents(partial, [...events, ...events]);
    return { replay: module.replayThrough(expected, recovered, expected.last_sequence), count: recovered.length };
  }, { events, expected: withdrawn });
  assert.deepEqual(parity.replay, withdrawn);
  assert.equal(parity.count, events.length);
  checks.push('Actual browser reducer replays persisted log exactly, recovers missing events and deduplicates deliveries');

  await page.getByRole('button', { name: /S1.*Synthetic engineering source/ }).last().click();
  await page.getByRole('button', { name: 'Restore source availability' }).click();
  await page.getByRole('button', { name: 'Simulate source withdrawal' }).waitFor();
  const restored = await json('/runs/' + runId + '/snapshot');
  assert.equal(restored.claims.find(row => row.claim_id === 'A').status, 'needs_review');
  assert.equal(restored.claims.find(row => row.claim_id === 'B').status, 'supported');
  assert.deepEqual(restored.claims.find(row => row.claim_id === 'C'), initial.claims.find(row => row.claim_id === 'C'));
  checks.push('Restoring source availability requires review and does not automatically recertify A');

  await page.getByRole('button', { name: 'New run', exact: true }).click();
  await page.getByRole('button', { name: /Open scientific sources/ }).click();
  await page.getByText('Imported scientific sources', { exact: true }).waitFor();
  const sourceRun = new URL(page.url()).searchParams.get('run');
  const sources = await json('/runs/' + sourceRun + '/snapshot');
  assert.equal(sources.sources.length, 2);
  assert.equal(sources.claims.length, 0);
  checks.push('Browser imports two real pinned source records without fabricated claims');
  const alias = await json('/tools/resolve-gene?mention=Ten-a');
  assert.equal(alias.gene_id, 'FBgn0267001');
  const ambiguous = await json('/tools/resolve-gene?mention=Teneurin');
  assert.equal(ambiguous.status, 'ambiguous');
  assert.equal(ambiguous.candidate_count, 2);
  for (const candidate of ambiguous.candidates) {
    assert.equal((await json('/tools/resolve-gene?mention=' + candidate.gene_id)).gene_id, candidate.gene_id);
  }
  assert.equal((await json('/tools/resolve-gene?mention=Ten-a&taxon=NCBITaxon%3A9606')).status, 'taxon_mismatch');
  const ambiguousSearch = await fetch(apiUrl + '/runs/' + sourceRun + '/search?gene_id=Teneurin&query=matching');
  assert.equal(ambiguousSearch.status, 422);
  assert.equal((await ambiguousSearch.json()).code, 'gene_ambiguous');
  const anatomy = await json('/tools/resolve-term?mention=primary%20spermatocyte&ontology=FBbt');
  assert.equal(anatomy.term_id, 'FBbt:00005286');
  assert.equal((await json('/tools/resolve-term?mention=adult%20stage&ontology=FBdv')).term_id, 'FBdv:00005369');
  const obsolete = await json('/tools/resolve-term?mention=FBdv%3A00005329&ontology=FBdv');
  assert.equal(obsolete.status, 'obsolete');
  assert.equal(obsolete.term_id, null);
  assert.deepEqual(obsolete.candidates[0].replaced_by, ['FBdv:00005330']);
  assert.equal((await json('/tools/resolve-term?mention=adult%20stage%20I&ontology=FBdv')).status, 'not_found');
  checks.push('Pinned lookup resolves gene/term identity, preserves aliases and taxon ambiguity, and leaves obsolete/broad terms unaccepted');
  await page.screenshot({ path: path.join(artifactDir, '03-sources.png'), fullPage: true });

  await page.getByRole('button', { name: /PMC3345284.*Teneurins/ }).last().click();
  await page.getByLabel('Gene identity', { exact: true }).fill('Ten-a');
  await page.getByLabel('Decision-relevant search').fill('DA1 VA1d matching');
  await page.getByRole('button', { name: 'Search source passages' }).click();
  await page.getByRole('button', { name: /Read exact spans/ }).first().click();
  const displayedQuote = await page.locator('.read-span blockquote').first().innerText();
  const acceptedRequest = page.waitForRequest(request => request.method() === 'POST' && request.url().endsWith('/evidence'));
  await page.getByRole('button', { name: 'Pin evidence', exact: true }).first().click();
  const pinBody = (await acceptedRequest).postDataJSON();
  await page.getByText('1 pinned', { exact: true }).waitFor();
  const withEvidence = await json('/runs/' + sourceRun + '/snapshot');
  assert.equal(withEvidence.evidence.length, 1);
  assert.equal(withEvidence.claims.length, 0);
  const evidenceId = withEvidence.evidence[0].evidence_id;
  const detail = await json('/runs/' + sourceRun + '/evidence/' + evidenceId);
  assert.equal(detail.quote, displayedQuote);
  assert.equal(createHash('sha256').update(detail.quote).digest('hex'), detail.quote_sha256);
  assert.equal(detail.source_version, withEvidence.sources.find(row => row.source_id === 'PMC3345284').source_version);
  checks.push('Real paper search → canonical span read → browser pin → MongoDB evidence → exact quote/hash reconstruction');

  stop(apiProcess, 'SIGKILL');
  await new Promise(resolve => apiProcess.once('exit', resolve));
  apiProcess = startApi();
  await ready(apiUrl + '/health');
  const retriedPin = await json('/runs/' + sourceRun + '/evidence', post(pinBody));
  assert.equal(retriedPin.replayed, true);
  assert.equal((await json('/runs/' + sourceRun + '/snapshot')).evidence.length, 1);
  await page.reload();
  await page.getByRole('button', { name: /PMC3345284.*Teneurins/ }).last().click();
  await page.getByRole('button', { name: /Inspect pinned passage 1/ }).click();
  await page.getByText('Server-reconstructed', { exact: true }).waitFor();
  checks.push('Fresh API process accepts canonical span retry without duplicate evidence and browser reopens pinned evidence');

  const badVersion = await fetch(apiUrl + '/runs/' + sourceRun + '/evidence', post({ ...pinBody, operation_id: 'bad-version', source_version: '0'.repeat(64) }));
  assert.equal(badVersion.status, 422);
  const forgedSpan = await fetch(apiUrl + '/runs/' + sourceRun + '/evidence', post({ ...pinBody, operation_id: 'bad-span', span_ids: [pinBody.span_ids[0] + 'forged'] }));
  assert.equal(forgedSpan.status, 422);
  const missingChunk = await fetch(apiUrl + '/runs/' + sourceRun + '/chunks/nonexistent?source_version=' + detail.source_version);
  assert.equal(missingChunk.status, 404);
  const unknownField = await fetch(apiUrl + '/runs', post({ mode: 'fixture', secret: 'must-not-echo' }));
  assert.equal(unknownField.status, 422);
  assert(!(await unknownField.text()).includes('must-not-echo'));
  checks.push('Changed source version and forged span rejected; invalid request fields are not echoed');

  assert.deepEqual(errors, [], 'Uncaught browser errors');
  const report = {
    result: 'passed', scope: 'Engineering browser/API/local MongoDB E2E; no model, Atlas or LangGraph execution',
    run_id: runId, source_run_id: sourceRun, database,
    commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
    manifest_sha256: createHash('sha256').update(await readFile(path.join(root, 'data/manifests/showcase.json'))).digest('hex'),
    source_versions: sources.sources.map(row => ({ source_id: row.source_id, source_version: row.source_version })),
    model_id: null, policy_version: 'fixture-v1 (engineering fixture only)',
    started_at: new Date(startedAt).toISOString(), duration_seconds: (Date.now() - startedAt) / 1000,
    checks, artifact_directory: artifactDir,
  };
  await writeFile(path.join(artifactDir, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  console.error(error);
  await writeFile(path.join(artifactDir, 'failure.json'), JSON.stringify({ error: error.message, checks }, null, 2));
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  services.forEach(child => stop(child));
  await writeFile(path.join(artifactDir, 'services.log'), logs.join(''));
}
