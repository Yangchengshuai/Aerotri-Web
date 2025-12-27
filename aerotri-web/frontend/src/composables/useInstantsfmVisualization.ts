import { ref, onUnmounted } from 'vue'
import type { RealtimeUpdate } from '@/types'

export function useInstantsfmVisualization(blockId: string) {
  const connected = ref(false)
  const update = ref<RealtimeUpdate | null>(null)
  const error = ref<string | null>(null)
  
  let ws: WebSocket | null = null
  let reconnectTimer: number | null = null
  let pingInterval: number | null = null

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws/visualization/${blockId}`
    
    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      error.value = null
      
      // Start ping interval to keep connection alive
      pingInterval = window.setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 30000) // Ping every 30 seconds
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as RealtimeUpdate
        update.value = data
      } catch {
        // Handle non-JSON messages (like "pong")
        if (event.data === 'pong') {
          // Connection is alive
          return
        }
        console.error('Failed to parse visualization WebSocket message:', event.data)
      }
    }

    ws.onerror = () => {
      error.value = 'WebSocket connection error'
    }

    ws.onclose = () => {
      connected.value = false
      if (pingInterval !== null) {
        clearInterval(pingInterval)
        pingInterval = null
      }
      
      // Attempt to reconnect after 3 seconds
      if (reconnectTimer === null) {
        reconnectTimer = window.setTimeout(() => {
          reconnectTimer = null
          connect()
        }, 3000)
      }
    }
  }

  function disconnect() {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (pingInterval !== null) {
      clearInterval(pingInterval)
      pingInterval = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
  }

  function requestStatus() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send('status')
    }
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    update,
    error,
    connect,
    disconnect,
    requestStatus,
  }
}

