import type { Decision, Evaluation, Investigation, Policy, RunSnapshot } from '../contracts';
import { Icon } from '../app/Icon';
import './harness.css';

const humanize = (value: string) => value.replaceAll('_', ' ');
const fields = [
  { section: 'context_policy', key: 'mode', label: 'Evidence context' },
  { section: 'review_policy', key: 'mode', label: 'Scientific review' },
  { section: 'review_policy', key: 'retrieve_controls', label: 'Retrieve controls' },
] as const;
const modeLabels: Record<string, string> = {
  ranked_passages: 'Ranked passages', experimental_context: 'Experimental context',
  on_conflict: 'When evidence conflicts', on_scope_ambiguity: 'When scope is ambiguous', always: 'Every investigation',
};

function fieldValue(policy: Policy, section: string, key: string): unknown {
  const value = policy.configuration[section];
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>)[key] : undefined;
}

function displayValue(value: unknown): string {
  if (value === undefined || value === null) return 'Not recorded';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'string') return modeLabels[value] ?? humanize(value);
  return 'Unrecognized setting';
}

function cost(value: unknown, currency: unknown): string {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return 'Unknown';
  const amount = value === 0 ? '0.00' : value.toLocaleString('en-US', { maximumSignificantDigits: 6, useGrouping: false });
  return currency === 'USD' ? `$${amount} USD` : `${amount} · currency not recorded`;
}

function Hash({ value }: { value: string }) {
  return <code title={value}>{value.length > 22 ? `${value.slice(0, 10)}…${value.slice(-8)}` : value}</code>;
}

function EvaluationRecord({ evaluation }: { evaluation: Evaluation }) {
  const flags = Object.entries(evaluation.integrity_outcomes).filter((entry): entry is [string, boolean] => typeof entry[1] === 'boolean');
  return <section className="harness-evaluation" aria-label={`${evaluation.arm} ${humanize(evaluation.split)} evaluation`}>
    <div className="harness-evaluation-heading"><strong>{evaluation.arm}</strong><span>{humanize(evaluation.split)}</span></div>
    <dl className="harness-counts">
      <div><dt>Correct decisions</dt><dd>{evaluation.correct_count} / {evaluation.decision_count}</dd></div>
      <div><dt>Support audit</dt><dd>{evaluation.supported_count} / {evaluation.support_count}</dd></div>
      <div><dt>Reference matches</dt><dd>{evaluation.reference_hits} / {evaluation.reference_count}</dd></div>
      <div><dt>Scheduled cases</dt><dd>{evaluation.case_ids.length}</dd></div>
      <div><dt>Recorded failures</dt><dd>{evaluation.failures.length}</dd></div>
    </dl>
    <div className="harness-costs"><div><span>Investigation + review cost</span><strong>{cost(evaluation.usage.total_cost, evaluation.usage.currency)}</strong></div><div><span>Optimizer cost · separate</span><strong>{cost(evaluation.usage.optimizer_cost, evaluation.usage.currency)}</strong></div></div>
    {evaluation.usage.total_cost == null && <p className="harness-note">No total cost was recorded. This is not a zero-cost run.</p>}
    {evaluation.split === 'final_test' && <p className="harness-note">Final-test results are report-only. They do not select the policy.</p>}
    <details className="harness-provenance"><summary>Evaluation provenance <Icon name="chevron" size={11} /></summary><dl><div><dt>Record</dt><dd><Hash value={evaluation.evaluation_id} /></dd></div><div><dt>Model</dt><dd>{evaluation.model_id || 'Not recorded'}</dd></div><div><dt>Manifest</dt><dd><Hash value={evaluation.manifest_sha256} /></dd></div><div><dt>Policy</dt><dd><Hash value={evaluation.policy_sha256} /></dd></div><div><dt>Predictions</dt><dd><Hash value={evaluation.prediction_sha256} /></dd></div></dl><p className="harness-case-list"><strong>Cases</strong> {evaluation.case_ids.length ? evaluation.case_ids.join(', ') : 'None recorded'}</p>{flags.length > 0 && <ul className="harness-checks">{flags.map(([name, passed]) => <li key={name} className={passed ? 'passed' : 'failed'}><Icon name={passed ? 'check' : 'warning'} size={11} /><span>{humanize(name)}</span><strong>{passed ? 'Passed' : 'Failed'}</strong></li>)}</ul>}</details>
  </section>;
}

function RecordedActions({ investigations, decisions }: { investigations: Investigation[]; decisions: Decision[] }) {
  if (!investigations.length) return <p className="harness-note"><Icon name="clock" size={12} />Execution trace not recorded for this policy.</p>;
  return <details className="harness-execution"><summary><span>Recorded investigation actions</span><span>{investigations.length} {investigations.length === 1 ? 'investigation' : 'investigations'}</span></summary>{investigations.map(investigation => {
    const actions = decisions.filter(decision => decision.investigation_id === investigation.investigation_id);
    return <div className="harness-investigation" key={investigation.investigation_id}><div><strong>{investigation.question}</strong><span>{humanize(investigation.status)}</span></div>{actions.length ? <ol>{actions.map(decision => <li key={decision.decision_id}><strong>{humanize(decision.selected_action)}</strong><p>{decision.reason_summary}</p></li>)}</ol> : <p className="harness-note">No action decisions recorded yet.</p>}<span className="harness-workflow">Workflow <Hash value={investigation.workflow_id} /></span></div>;
  })}</details>;
}

function PolicyRecord({ policy, snapshot }: { policy: Policy; snapshot: RunSnapshot }) {
  const parent = snapshot.policies.find(row => row.policy_version === policy.parent_policy_version);
  const changedFields = parent ? fields.filter(field => fieldValue(policy, field.section, field.key) !== fieldValue(parent, field.section, field.key)) : [];
  const evaluations = snapshot.evaluations.filter(row => row.policy_sha256 === policy.configuration_sha256 || row.evaluation_id === policy.evaluation_id);
  const investigations = snapshot.investigations.filter(row => row.policy_version === policy.policy_version);
  const status = policy.selection_status;
  const contextMode = fieldValue(policy, 'context_policy', 'mode');
  const reviewMode = fieldValue(policy, 'review_policy', 'mode');
  const statusClass = status === 'promoted' ? 'promoted' : status === 'rejected' ? 'rejected' : 'pending';
  return <article className="harness-policy" aria-label={`Policy ${policy.policy_version}`}>
    <div className="harness-policy-heading"><strong>{policy.policy_version}</strong><span className={`harness-selection ${statusClass}`}><Icon name={status === 'promoted' ? 'check' : status === 'rejected' ? 'warning' : 'clock'} size={11} />{status ? humanize(status) : 'Selection not recorded'}</span></div>
    <p className="harness-proposer">Proposed by <strong>{policy.proposed_by || 'not recorded'}</strong></p>
    <span className="eyebrow">Configured investigation route</span>
    <div className="harness-route"><div><Icon name="book" size={13} /><span>Assemble evidence</span><strong>{displayValue(contextMode)}</strong></div><Icon name="arrow" size={13} /><div><Icon name="shield" size={13} /><span>Review scope</span><strong>{displayValue(reviewMode)}</strong></div></div>
    <p className="harness-controls">Retrieve experimental controls: <strong>{displayValue(fieldValue(policy, 'review_policy', 'retrieve_controls'))}</strong></p>
    <div className="harness-diff"><span className="eyebrow">{parent ? `Changes from ${parent.policy_version}` : policy.parent_policy_version ? 'Parent comparison unavailable' : 'Initial policy'}</span>{parent ? changedFields.length ? <table><thead><tr><th>Setting</th><th>Before</th><th>Proposed</th></tr></thead><tbody>{changedFields.map(field => <tr key={`${field.section}.${field.key}`}><th scope="row">{field.label}</th><td>{displayValue(fieldValue(parent, field.section, field.key))}</td><td>{displayValue(fieldValue(policy, field.section, field.key))}</td></tr>)}</tbody></table> : <p>No changes to the allowed context and review settings.</p> : <p>{policy.parent_policy_version ? `Parent ${policy.parent_policy_version} is not present in this record.` : 'No earlier policy is recorded for comparison.'}</p>}</div>
    {policy.development_failure_ids.length > 0 && <details className="harness-provenance"><summary>Development evidence <span>{policy.development_failure_ids.length} linked records</span></summary><ul className="harness-failures">{policy.development_failure_ids.map(id => <li key={id}><code>{id}</code></li>)}</ul></details>}
    <RecordedActions investigations={investigations} decisions={snapshot.decisions} />
    <details className="harness-provenance"><summary>Policy configuration <Icon name="chevron" size={11} /></summary><p className="harness-note">Immutable configuration hash <Hash value={policy.configuration_sha256} /></p><pre>{JSON.stringify(policy.configuration, null, 2)}</pre></details>
    <div className="harness-evaluations-title"><Icon name="branch" size={12} /><strong>Recorded evaluations</strong></div>{evaluations.length ? evaluations.map(evaluation => <EvaluationRecord key={evaluation.evaluation_id} evaluation={evaluation} />) : <p className="harness-note">No evaluation is linked to this policy. Performance and cost are unknown.</p>}
    {status === 'rejected' && <p className="harness-outcome rejected">Candidate rejected. This record does not establish improvement.</p>}{status === 'promoted' && <p className="harness-outcome promoted">Candidate promoted by the recorded selection decision.</p>}
  </article>;
}

export function HarnessPanel({ snapshot }: { snapshot: RunSnapshot }) {
  const unlinked = snapshot.evaluations.filter(evaluation => !snapshot.policies.some(policy => evaluation.policy_sha256 === policy.configuration_sha256 || evaluation.evaluation_id === policy.evaluation_id));
  const hasRecords = snapshot.policies.length > 0 || snapshot.evaluations.length > 0;
  return <details className="harness-panel harness-panel-v2"><summary><span><Icon name="spark" size={15} />Harness evolution</span><span>{hasRecords ? `${snapshot.policies.length} policies · ${snapshot.evaluations.length} evaluations` : 'Pending'}</span></summary><div className="harness-content">
    {!hasRecords ? <div className="harness-empty"><Icon name="clock" size={19} /><strong>Awaiting an evaluated proposal</strong><p>No policy proposal or evaluation has been recorded. The panel will show the proposed change, recorded actions, and selection result when they exist.</p><span>Performance and cost: unknown</span></div> : <>
      <p className="harness-intro">Stored policies and evaluation counts at this point in the run. Configured routes describe policy settings; recorded actions show what executed.</p>
      {snapshot.mode === 'fixture' && <p className="harness-fixture"><Icon name="warning" size={12} />Synthetic run. These records are not measured scientific performance.</p>}
      {snapshot.policies.map(policy => <PolicyRecord key={policy.policy_version} policy={policy} snapshot={snapshot} />)}
      {unlinked.length > 0 && <section className="harness-unlinked"><h3>Other recorded evaluations</h3><p className="harness-note">The matching policy record is not present.</p>{unlinked.map(evaluation => <EvaluationRecord key={evaluation.evaluation_id} evaluation={evaluation} />)}</section>}
    </>}
  </div></details>;
}
