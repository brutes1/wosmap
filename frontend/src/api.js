/**
 * API client for the tactile map generator backend.
 */

const API_BASE = '/api'

/**
 * Submit a map generation request.
 */
export async function createMap(params) {
  const response = await fetch(`${API_BASE}/maps`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create map')
  }

  return response.json()
}

/**
 * Get the status of a map generation job.
 */
export async function getMapStatus(jobId) {
  const response = await fetch(`${API_BASE}/maps/${jobId}`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get map status')
  }

  return response.json()
}

/**
 * Get the download URL for a completed map.
 */
export function getDownloadUrl(jobId, fileType = 'stl') {
  return `${API_BASE}/maps/${jobId}/download?file_type=${fileType}`
}

/**
 * Get history of all map generation jobs.
 */
export async function getHistory() {
  const response = await fetch(`${API_BASE}/maps`)
  if (!response.ok) {
    throw new Error('Failed to get history')
  }
  return response.json()
}

/**
 * Clear all map generation history and delete files.
 */
export async function clearHistory() {
  const response = await fetch(`${API_BASE}/maps`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error('Failed to clear history')
  }
  return response.json()
}

/**
 * Configure the Bambu X1C printer.
 */
export async function configurePrinter(config) {
  const response = await fetch(`${API_BASE}/printer/config`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to configure printer')
  }

  return response.json()
}

/**
 * Get the current printer configuration.
 */
export async function getPrinterConfig() {
  const response = await fetch(`${API_BASE}/printer/config`)
  return response.json()
}

/**
 * Send a completed map to the printer.
 */
export async function sendToPrinter(jobId) {
  const response = await fetch(`${API_BASE}/maps/${jobId}/print`, {
    method: 'POST',
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to send to printer')
  }

  return response.json()
}

/**
 * Poll for job completion.
 * @param {string} jobId - The job ID to poll
 * @param {function} onStatusUpdate - Optional callback called with status object on each poll
 * @param {number} interval - Polling interval in ms (default 2000)
 * @param {number} maxAttempts - Maximum poll attempts (default 300)
 */
export async function pollUntilComplete(jobId, onStatusUpdate = null, interval = 2000, maxAttempts = 300) {
  for (let i = 0; i < maxAttempts; i++) {
    const status = await getMapStatus(jobId)

    // Call the status update callback if provided
    if (onStatusUpdate) {
      onStatusUpdate(status)
    }

    if (status.status === 'completed') {
      return status
    }

    if (status.status === 'failed') {
      throw new Error(status.error || 'Map generation failed')
    }

    await new Promise(resolve => setTimeout(resolve, interval))
  }

  throw new Error('Timeout waiting for map generation')
}
