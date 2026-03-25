import { useEffect, useRef, useState, useCallback } from 'react'
import cytoscape, { Core, EventObject } from 'cytoscape'
import type { GraphData, GraphNode } from '../App'

// @ts-ignore
import coseBilkent from 'cytoscape-cose-bilkent'

// Register layout
try {
  cytoscape.use(coseBilkent)
} catch (e) {
  // Already registered
}

const ENTITY_COLORS: Record<string, string> = {
  'Sales Order': '#6366f1',
  'Sales Order Item': '#818cf8',
  'Delivery': '#06b6d4',
  'Delivery Item': '#22d3ee',
  'Billing Document': '#f59e0b',
  'Billing Document Item': '#fbbf24',
  'Journal Entry': '#8b5cf6',
  'Payment': '#10b981',
  'Customer': '#ec4899',
  'Product': '#f97316',
  'Plant': '#14b8a6',
  'Address': '#64748b',
}

const ENTITY_SIZES: Record<string, number> = {
  'Sales Order': 35,
  'Customer': 35,
  'Delivery': 30,
  'Billing Document': 30,
  'Journal Entry': 28,
  'Payment': 28,
  'Product': 25,
  'Plant': 25,
  'Sales Order Item': 18,
  'Delivery Item': 18,
  'Billing Document Item': 18,
  'Address': 20,
}

interface GraphViewerProps {
  data: GraphData
  onNodeClick: (node: GraphNode, position: { x: number; y: number }) => void
  onExpandNode: (nodeId: string) => void
  highlightedNodes: Set<string>
}

export default function GraphViewer({ data, onNodeClick, onExpandNode, highlightedNodes }: GraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const [showGranular, setShowGranular] = useState(false)

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current || !data) return

    // Filter out item-level nodes for cleaner default view
    const filteredNodes = showGranular
      ? data.nodes
      : data.nodes.filter(n =>
          !n.entity.includes('Item') && n.entity !== 'Address'
        )

    const filteredNodeIds = new Set(filteredNodes.map(n => n.id))
    const filteredEdges = data.edges.filter(
      e => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
    )

    const elements = [
      ...filteredNodes.map(node => ({
        data: {
          id: node.id,
          label: node.label,
          entity: node.entity,
          connections: node.connections,
          ...node.data,
        },
      })),
      ...filteredEdges.map((edge, i) => ({
        data: {
          id: `e-${i}-${edge.source}-${edge.target}`,
          source: edge.source,
          target: edge.target,
          relationship: edge.relationship,
        },
      })),
    ]

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'background-color': (ele: any) => {
              const entity = ele.data('entity')
              return ENTITY_COLORS[entity] || '#6b7280'
            },
            'width': (ele: any) => {
              const entity = ele.data('entity')
              return ENTITY_SIZES[entity] || 20
            },
            'height': (ele: any) => {
              const entity = ele.data('entity')
              return ENTITY_SIZES[entity] || 20
            },
            'font-size': '9px',
            'color': '#9aa0b4',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 6,
            'text-max-width': '80px',
            'text-wrap': 'ellipsis',
            'border-width': 2,
            'border-color': (ele: any) => {
              const entity = ele.data('entity')
              const color = ENTITY_COLORS[entity] || '#6b7280'
              return color
            },
            'border-opacity': 0.3,
            'text-opacity': 0.7,
            'min-zoomed-font-size': 8,
          } as any,
        },
        {
          selector: 'node.highlighted',
          style: {
            'border-width': 4,
            'border-color': '#f59e0b',
            'border-opacity': 1,
            'background-opacity': 1,
            'z-index': 999,
            'text-opacity': 1,
          } as any,
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#e8eaed',
            'border-opacity': 1,
          } as any,
        },
        {
          selector: 'edge',
          style: {
            'width': 1,
            'line-color': 'rgba(99, 102, 241, 0.15)',
            'target-arrow-color': 'rgba(99, 102, 241, 0.15)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.6,
          } as any,
        },
        {
          selector: 'edge.highlighted',
          style: {
            'width': 2,
            'line-color': 'rgba(245, 158, 11, 0.6)',
            'target-arrow-color': 'rgba(245, 158, 11, 0.6)',
          } as any,
        },
        {
          selector: 'node:active',
          style: {
            'overlay-opacity': 0,
          } as any,
        },
      ],
      layout: {
        name: 'cose-bilkent',
        // @ts-ignore
        quality: 'default',
        randomize: true,
        animate: false,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 120,
        nodeRepulsion: 8000,
        edgeElasticity: 0.45,
        nestingFactor: 0.1,
        gravity: 0.25,
        gravityRange: 3.8,
        numIter: 2500,
        tile: true,
        tilingPaddingVertical: 10,
        tilingPaddingHorizontal: 10,
      },
      minZoom: 0.1,
      maxZoom: 5,
      wheelSensitivity: 0.3,
    })

    // Event handlers
    cy.on('tap', 'node', (evt: EventObject) => {
      const node = evt.target
      const pos = node.renderedPosition()
      const nodeData: GraphNode = {
        id: node.id(),
        entity: node.data('entity'),
        label: node.data('label'),
        data: Object.fromEntries(
          Object.entries(node.data()).filter(
            ([k]) => !['id', 'label', 'entity', 'connections'].includes(k)
          )
        ),
        connections: node.data('connections'),
      }
      onNodeClick(nodeData, { x: pos.x + 20, y: pos.y - 20 })
    })

    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) {
        // Click on background - do nothing, let NodeDetail handle its own close
      }
    })

    cyRef.current = cy

    return () => {
      cy.destroy()
    }
  }, [data, showGranular, onNodeClick])

  // Handle highlighted nodes
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return

    cy.nodes().removeClass('highlighted')
    cy.edges().removeClass('highlighted')

    if (highlightedNodes.size > 0) {
      highlightedNodes.forEach(nodeId => {
        const node = cy.getElementById(nodeId)
        if (node.length > 0) {
          node.addClass('highlighted')
          node.connectedEdges().addClass('highlighted')
        }
      })

      // Fit to highlighted nodes
      const highlightedElements = cy.nodes('.highlighted')
      if (highlightedElements.length > 0) {
        cy.animate({
          fit: { eles: highlightedElements, padding: 80 } as any,
          duration: 500,
        })
      }
    }
  }, [highlightedNodes])

  const handleFit = () => {
    cyRef.current?.fit(undefined, 50)
  }

  const toggleGranular = () => {
    setShowGranular(prev => !prev)
  }

  // Compute legend items from actual data
  const legendItems = data
    ? [...new Set(data.nodes.map(n => n.entity))]
        .filter(e => showGranular || (!e.includes('Item') && e !== 'Address'))
        .sort()
    : []

  const nodeCount = data ? data.nodes.length : 0
  const edgeCount = data ? data.edges.length : 0

  return (
    <>
      <div className="graph-container" ref={containerRef} />

      <div className="graph-controls">
        <button className="graph-btn" onClick={handleFit}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
          </svg>
          Fit View
        </button>
        <button className={`graph-btn ${showGranular ? 'active' : ''}`} onClick={toggleGranular}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
          </svg>
          {showGranular ? 'Hide' : 'Show'} Granular Overlay
        </button>
      </div>

      <div className="graph-legend">
        {legendItems.map(entity => (
          <div key={entity} className="legend-item">
            <div
              className="legend-dot"
              style={{ backgroundColor: ENTITY_COLORS[entity] || '#6b7280' }}
            />
            {entity}
          </div>
        ))}
      </div>

      <div className="graph-stats">
        {nodeCount} nodes · {edgeCount} edges
      </div>
    </>
  )
}
