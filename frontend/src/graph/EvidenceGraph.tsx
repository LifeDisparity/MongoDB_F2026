import { useMemo } from 'react';
import { ReactFlow, Background, BackgroundVariant, Controls, Handle, Position, type Node, type Edge, type NodeProps } from '@xyflow/react';
import type { Claim, RunSnapshot, SourceSnapshot } from '../contracts';
import { Icon } from '../app/Icon';

export type Selection = { kind: 'claim'; id: string } | { kind: 'source'; id: string; version: string } | null;
export const statusLabel = (status: string) => status.replaceAll('_', ' ');
export const relationLabel = (relation: string) => ({ expressed_in: 'Expression', perturbation_observation: 'Perturbation', involved_in: 'Function' }[relation] ?? relation);
const shortGene = (id: string) => id.startsWith('fixture-gene-') ? `Gene ${id.split('-').at(-1)}` : id;

function GeneNode({ data }: NodeProps<Node<{ name: string; count: number; fixture: boolean }>>) {
  return <div className="gene-node"><div className="gene-orbit"><Icon name="atlas" size={23} /><strong>{data.name}</strong><span>{data.fixture ? 'FIXTURE GENE' : 'GENE'}</span></div><div className="gene-count">{data.count} {data.count === 1 ? 'claim' : 'claims'}</div><Handle type="source" position={Position.Right} /></div>;
}

function ClaimNode({ data, selected }: NodeProps<Node<{ claim: Claim; updated: boolean }>>) {
  const claim = data.claim;
  const qualifier = claim.qualifiers;
  return <div className={`claim-node status-${claim.status} ${selected ? 'selected' : ''} ${data.updated ? 'event-updated' : ''}`}>
    <Handle type="target" position={Position.Left} />
    <div className="claim-node-top"><span className={`relation relation-${claim.relation}`}>{relationLabel(claim.relation)}</span><span className="node-id">{claim.claim_id}</span></div>
    <strong className="claim-title">{claim.object_label}</strong>
    <div className="claim-qualifiers">{[qualifier.cell_class, qualifier.intervention, qualifier.stage_label, qualifier.assay].filter(Boolean).slice(0, 2).map(value => <span key={String(value)}>{String(value)}</span>)}</div>
    <div className="claim-node-foot"><span className={`status status-${claim.status}`}><Icon name={claim.status === 'supported' ? 'check' : claim.status === 'candidate' ? 'clock' : 'warning'} size={12} />{statusLabel(claim.status)}</span><span>{claim.usable_evidence_ids.length}/{claim.evidence_ids.length} evidence</span></div>
    <Handle type="source" position={Position.Right} />
  </div>;
}

function SourceNode({ data, selected }: NodeProps<Node<{ source: SourceSnapshot; available: boolean }>>) {
  return <div className={`source-node ${data.available ? '' : 'source-unavailable'} ${selected ? 'selected' : ''}`}>
    <Handle type="target" position={Position.Left} />
    <div className="source-node-icon"><Icon name="book" size={17} /></div>
    <div><span className="eyebrow">{data.available ? 'Source available' : 'Source withdrawn'}</span><strong>{data.source.title}</strong><span className="source-node-id">{data.source.pmcid ?? data.source.source_id}</span></div>
  </div>;
}

const nodeTypes = { gene: GeneNode, claim: ClaimNode, source: SourceNode };

export function EvidenceGraph({ snapshot, selection, onSelect, changedIds }: { snapshot: RunSnapshot; selection: Selection; onSelect: (value: Selection) => void; changedIds: string[] }) {
  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const genes = [...new Set(snapshot.claims.map(claim => claim.gene_id))].sort();
    let lane = 0;
    for (const gene of genes) {
      const claims = snapshot.claims.filter(claim => claim.gene_id === gene).sort((a, b) => a.claim_id.localeCompare(b.claim_id));
      const start = lane;
      nodes.push({ id: `gene:${gene}`, type: 'gene', position: { x: 30, y: (start + (claims.length - 1) / 2) * 185 + 20 }, data: { name: shortGene(gene), count: claims.length, fixture: snapshot.mode === 'fixture' }, draggable: false, selectable: false, focusable: false });
      for (const claim of claims) {
        nodes.push({ id: `claim:${claim.claim_id}`, type: 'claim', position: { x: 260, y: lane * 185 }, data: { claim, updated: changedIds.includes(claim.claim_id) }, selected: selection?.kind === 'claim' && selection.id === claim.claim_id, draggable: false, ariaRole: 'button', ariaLabel: `Inspect claim ${claim.claim_id}: ${claim.object_label}, ${statusLabel(claim.status)}` });
        edges.push({ id: `gene-claim:${claim.claim_id}`, source: `gene:${gene}`, target: `claim:${claim.claim_id}`, type: 'smoothstep', className: `atlas-edge status-${claim.status}` });
        for (const evidenceId of [...claim.evidence_ids, ...claim.conflicting_evidence_ids]) {
          const evidence = snapshot.evidence.find(row => row.evidence_id === evidenceId);
          if (!evidence) continue;
          const conflict = claim.conflicting_evidence_ids.includes(evidenceId);
          const usable = [...claim.usable_evidence_ids, ...claim.usable_conflicting_evidence_ids].includes(evidenceId);
          edges.push({ id: `${claim.claim_id}:${evidenceId}`, source: `claim:${claim.claim_id}`, target: `source:${evidence.source_id}:${evidence.source_version}`, type: 'smoothstep', className: `evidence-edge ${usable ? 'available' : 'unavailable'} ${conflict ? 'conflicting' : ''}`, animated: changedIds.includes(claim.claim_id) && !usable, label: conflict ? 'conflicts' : undefined });
        }
        lane++;
      }
    }
    snapshot.sources.slice().sort((a, b) => a.source_id.localeCompare(b.source_id)).forEach((source, i) => {
      const state = snapshot.source_state.find(row => row.source_id === source.source_id && row.source_version === source.source_version);
      nodes.push({ id: `source:${source.source_id}:${source.source_version}`, type: 'source', position: { x: genes.length ? 677 : 155, y: i * 185 + 34 }, data: { source, available: state?.available ?? false }, selected: selection?.kind === 'source' && selection.id === source.source_id && selection.version === source.source_version, draggable: false, ariaRole: 'button', ariaLabel: `Inspect source ${source.source_id}: ${source.title}` });
    });
    return { nodes, edges };
  }, [snapshot, selection, changedIds, onSelect]);

  const inspectNode = (node: Node) => {
    if (node.type === 'claim') onSelect({ kind: 'claim', id: (node.data.claim as Claim).claim_id });
    if (node.type === 'source') { const source = node.data.source as SourceSnapshot; onSelect({ kind: 'source', id: source.source_id, version: source.source_version }); }
  };
  return <div className="graph-canvas" onKeyDownCapture={event => {
    if (!['Enter', ' ', 'Escape'].includes(event.key) || !(event.target instanceof HTMLElement)) return;
    const nodeId = event.target.closest<HTMLElement>('.react-flow__node')?.dataset.id;
    const node = nodes.find(item => item.id === nodeId);
    if (!node || !['claim', 'source'].includes(node.type ?? '')) return;
    event.preventDefault(); event.stopPropagation();
    if (event.key === 'Escape') onSelect(null); else inspectNode(node);
  }}><ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.07, maxZoom: 1 }} minZoom={0.3} maxZoom={1.6} nodesDraggable={false} nodesConnectable={false} edgesFocusable={false} deleteKeyCode={null} ariaLabelConfig={{ 'node.a11yDescription.default': 'Press Enter or Space to inspect this record. Press Escape to close the inspector.' }} onNodeClick={(_event, node) => inspectNode(node)} onPaneClick={() => onSelect(null)} proOptions={{ hideAttribution: true }} aria-label="Scientific evidence graph">
    <Background variant={BackgroundVariant.Dots} color="#364147" gap={24} size={1} />
    <Controls showInteractive={false} position="bottom-left" />
  </ReactFlow></div>;
}
