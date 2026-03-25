import { useState, useEffect, useCallback } from 'react'
import GraphViewer from './components/GraphViewer'
import ChatPanel from './components/ChatPanel'
import NodeDetail from './components/NodeDetail'

// Types
export interface GraphNode {
  id: string
  entity: string
  label: string
  data: Record<string, any>
  connections: number
}

export interface GraphEdge {
  source: string
  target: string
  relationship: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface ChatMessage {
  role: 'user' | 'bot'
  content: string
  sql?: string
  referenced_nodes?: string[]
  timestamp: Date
}

const API_BASE = '/api'

function App() {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [nodePosition, setNodePosition] = useState<{ x: number; y: number } | null>(null)
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(new Set())
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'bot',
      content: 'Hi! I can help you analyze the **Order to Cash** process. Ask me about sales orders, deliveries, billing documents, payments, or any relationships between them.',
      timestamp: new Date(),
    },
  ])

  // Fetch initial graph
  useEffect(() => {
    fetchGraph()
  }, [])

  const fetchGraph = async () => {
    try {
      const response = await fetch(`${API_BASE}/graph?max_nodes=500`)
      const data = await response.json()
      setGraphData(data)
    } catch (error) {
      console.error('Failed to fetch graph:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleNodeClick = useCallback((node: GraphNode, position: { x: number; y: number }) => {
    setSelectedNode(node)
    setNodePosition(position)
  }, [])

  const handleNodeClose = useCallback(() => {
    setSelectedNode(null)
    setNodePosition(null)
  }, [])

  const handleExpandNode = useCallback(async (nodeId: string) => {
    try {
      const response = await fetch(`${API_BASE}/graph/expand/${encodeURIComponent(nodeId)}?depth=1`)
      const data = await response.json()
      
      if (graphData) {
        // Merge new nodes and edges
        const existingNodeIds = new Set(graphData.nodes.map(n => n.id))
        const existingEdgeKeys = new Set(graphData.edges.map(e => `${e.source}-${e.target}`))
        
        const newNodes = data.nodes.filter((n: GraphNode) => !existingNodeIds.has(n.id))
        const newEdges = data.edges.filter((e: GraphEdge) => !existingEdgeKeys.has(`${e.source}-${e.target}`))
        
        setGraphData({
          nodes: [...graphData.nodes, ...newNodes],
          edges: [...graphData.edges, ...newEdges],
        })
      }
    } catch (error) {
      console.error('Failed to expand node:', error)
    }
  }, [graphData])

  const handleChatMessage = useCallback(async (message: string) => {
    // Add user message
    const userMsg: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])

    try {
      // Build conversation history for the API
      const conversationHistory = messages
        .filter(m => m.role === 'user' || m.role === 'bot')
        .map(m => ({
          role: m.role === 'user' ? 'user' : 'model',
          parts: [m.content],
        }))

      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          conversation_history: conversationHistory,
        }),
      })

      const data = await response.json()

      // Add bot response
      const botMsg: ChatMessage = {
        role: 'bot',
        content: data.answer,
        sql: data.sql,
        referenced_nodes: data.referenced_nodes,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, botMsg])

      // Highlight referenced nodes
      if (data.referenced_nodes && data.referenced_nodes.length > 0) {
        setHighlightedNodes(new Set(data.referenced_nodes))
        // Clear highlight after 10 seconds
        setTimeout(() => setHighlightedNodes(new Set()), 10000)
      }
    } catch (error) {
      const errorMsg: ChatMessage = {
        role: 'bot',
        content: 'Sorry, I encountered an error connecting to the server. Please make sure the backend is running.',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMsg])
    }
  }, [messages])

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="loading-spinner" />
        <div className="loading-text">Building graph from SAP Order-to-Cash data...</div>
      </div>
    )
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-logo">D</div>
        <nav className="header-breadcrumb">
          <a href="/">Mapping</a>
          <span className="separator">/</span>
          <span className="current">Order to Cash</span>
        </nav>
      </header>

      {/* Main Content */}
      <div className="main-content">
        {/* Graph Panel */}
        <div className="graph-panel">
          {graphData && (
            <GraphViewer
              data={graphData}
              onNodeClick={handleNodeClick}
              onExpandNode={handleExpandNode}
              highlightedNodes={highlightedNodes}
            />
          )}

          {/* Node Detail Popup */}
          {selectedNode && nodePosition && (
            <NodeDetail
              node={selectedNode}
              position={nodePosition}
              onClose={handleNodeClose}
              onExpand={() => handleExpandNode(selectedNode.id)}
            />
          )}
        </div>

        {/* Chat Panel */}
        <ChatPanel
          messages={messages}
          onSendMessage={handleChatMessage}
        />
      </div>
    </div>
  )
}

export default App
