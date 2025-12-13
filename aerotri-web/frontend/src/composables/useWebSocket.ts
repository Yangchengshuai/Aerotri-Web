import { ref, onUnmounted } from 'vue'
import type { ProgressMessage } from '@/types'

export function useWebSocket(blockId: string) {
  const connected = ref(false)
  const progress = ref<ProgressMessage | null>(null)
  const error = ref<string | null>(null)
  
  let ws: WebSocket | null = null
  let reconnectTimer: number | null = null

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws/blocks/${blockId}/progress`
    
    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      error.value = null
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ProgressMessage
        progress.value = data
      } catch {
        console.error('Failed to parse WebSocket message:', event.data)
      }
    }

    ws.onerror = () => {
      error.value = 'WebSocket connection error'
    }

    ws.onclose = () => {
      connected.value = false
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
    progress,
    error,
    connect,
    disconnect,
    requestStatus,
  }
}
