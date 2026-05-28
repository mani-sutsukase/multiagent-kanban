import { ref, onUnmounted } from 'vue'

export function useWebSocket() {
  const ws = ref(null)
  const connected = ref(false)
  const handlers = {}
  let reconnectTimer = null
  let heartbeatTimer = null

  function connect() {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) return

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/ws`

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      connected.value = true
      startHeartbeat()
    }

    ws.value.onclose = () => {
      connected.value = false
      stopHeartbeat()
      scheduleReconnect()
    }

    ws.value.onerror = () => {
      connected.value = false
    }

    ws.value.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'ping') {
          send({ type: 'pong' })
          return
        }
        const handler = handlers[msg.type]
        if (handler) {
          handler(msg)
        }
      } catch (e) {
        console.error('WebSocket message error:', e)
      }
    }
  }

  function send(data) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(data))
    }
  }

  function on(eventType, handler) {
    handlers[eventType] = handler
  }

  function off(eventType) {
    delete handlers[eventType]
  }

  function startHeartbeat() {
    heartbeatTimer = setInterval(() => {
      send({ type: 'ping' })
    }, 30000)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) return
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, 3000)
  }

  function disconnect() {
    stopHeartbeat()
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    connect,
    disconnect,
    send,
    on,
    off,
  }
}
