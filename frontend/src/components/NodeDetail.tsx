import { useState } from 'react'
import type { GraphNode } from '../App'

// Fields to always show at the top
const PRIORITY_FIELDS = ['entity', 'salesOrder', 'deliveryDocument', 'billingDocument', 'accountingDocument', 'customer', 'product', 'plant', 'material', 'totalNetAmount', 'transactionCurrency']

// Fields to hide by default
const HIDDEN_FIELDS = ['lastChangeDateTime', 'lastChangeDate', 'creationTime', 'createdByUser', 'id']

interface NodeDetailProps {
  node: GraphNode
  position: { x: number; y: number }
  onClose: () => void
  onExpand: () => void
}

export default function NodeDetail({ node, position, onClose, onExpand }: NodeDetailProps) {
  const [showAll, setShowAll] = useState(false)

  // Merge entity into data for display
  const allFields: [string, any][] = [
    ['Entity', node.entity],
    ...Object.entries(node.data).filter(([k]) => k !== 'entity'),
  ]

  // Sort: priority fields first, then rest
  const prioritySet = new Set(PRIORITY_FIELDS)
  const hiddenSet = new Set(HIDDEN_FIELDS)

  const visibleFields = showAll
    ? allFields
    : allFields.filter(([k]) => !hiddenSet.has(k))

  // Sort: priority first
  visibleFields.sort((a, b) => {
    const aPriority = prioritySet.has(a[0].charAt(0).toLowerCase() + a[0].slice(1)) ? 0 : 1
    const bPriority = prioritySet.has(b[0].charAt(0).toLowerCase() + b[0].slice(1)) ? 0 : 1
    return aPriority - bPriority
  })

  // Take only first N if not showing all
  const displayFields = showAll ? visibleFields : visibleFields.slice(0, 12)
  const hiddenCount = allFields.length - displayFields.length

  // Position the popup, clamping to viewport
  const style: React.CSSProperties = {
    left: Math.min(position.x, window.innerWidth - 380),
    top: Math.min(Math.max(position.y, 60), window.innerHeight - 520),
  }

  return (
    <div className="node-detail" style={style}>
      <div className="node-detail-header">
        <div>
          <div className="node-detail-title">{node.label}</div>
          <div className="node-detail-entity">{node.entity}</div>
        </div>
        <button className="node-detail-close" onClick={onClose}>×</button>
      </div>

      <div className="node-detail-body">
        {displayFields.map(([key, value]) => (
          <div key={key} className="node-detail-field">
            <span className="node-detail-key">{formatFieldName(key)}</span>
            <span className="node-detail-value">{formatValue(value)}</span>
          </div>
        ))}
      </div>

      <div className="node-detail-footer">
        <div>
          {hiddenCount > 0 && (
            <button
              className="node-detail-toggle"
              onClick={() => setShowAll(prev => !prev)}
            >
              {showAll
                ? 'Hide extra fields'
                : `${hiddenCount} additional fields hidden for readability`}
            </button>
          )}
        </div>
        <span className="node-detail-connections">
          Connections: {node.connections}
        </span>
      </div>
    </div>
  )
}

function formatFieldName(key: string): string {
  // Convert camelCase to Title Case with colon
  return key
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, s => s.toUpperCase())
    .trim() + ':'
}

function formatValue(value: any): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  return String(value)
}
