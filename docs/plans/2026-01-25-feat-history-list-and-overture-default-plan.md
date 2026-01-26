---
title: History List with Stats and Overture Default
type: feat
date: 2026-01-25
---

# History List with Stats and Overture Default

## Overview

Add a history section showing previously generated maps with their stats and download buttons. Also change the default data source from OSM to Overture since testing confirmed Overture provides more complete building data.

## Problem Statement

1. Users generate maps but have no way to see previously generated files
2. The current default is "osm" but Overture provides more building coverage (+7% more triangles in testing)
3. No way to clear old generated files to free up disk space

## Proposed Solution

### Part 1: Default to Overture

Change `dataSource` default from `'osm'` to `'overture'` in `App.vue`.

### Part 2: History List

Add a collapsible "History" section below the results that shows all completed jobs:
- Location name
- File size (human-readable)
- Triangle count
- Creation date
- Download STL button

### Part 3: Clear History

Add a "Clear History" button that:
- Calls a new backend endpoint to delete all job files
- Clears the history from Redis
- Shows confirmation before deleting

## Technical Approach

### Files to Modify

1. **`frontend/src/App.vue`** - Add history section, change default
2. **`frontend/src/api.js`** - Add getHistory() and clearHistory() functions
3. **`backend/main.py`** - Add GET /api/maps (list) and DELETE /api/maps (clear) endpoints

### Backend Changes

#### New endpoint: GET /api/maps

Returns list of all jobs (completed or otherwise):

```python
@app.get("/api/maps")
async def list_maps():
    """List all map generation jobs."""
    r = get_redis()
    jobs = []

    # Get all result keys
    for key in r.scan_iter("result:*"):
        data = json.loads(r.get(key))
        job_id = key.replace("result:", "")
        jobs.append({
            "job_id": job_id,
            "status": data.get("status"),
            "location_name": data.get("location_name"),
            "created_at": data.get("created_at"),
            "file_info": data.get("file_info"),
        })

    # Sort by created_at descending
    jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"jobs": jobs}
```

#### New endpoint: DELETE /api/maps

Deletes all completed jobs and their files:

```python
@app.delete("/api/maps")
async def clear_history():
    """Delete all completed map jobs and their files."""
    r = get_redis()
    deleted_count = 0

    for key in r.scan_iter("result:*"):
        data = json.loads(r.get(key))

        # Delete files if they exist
        files = data.get("files", {})
        for file_type, file_path in files.items():
            path = Path(file_path)
            if path.exists():
                # Delete the job directory
                if path.parent.exists():
                    shutil.rmtree(path.parent)
                    break  # All files in same dir

        # Delete Redis key
        r.delete(key)
        deleted_count += 1

    return {"deleted": deleted_count, "message": f"Deleted {deleted_count} jobs"}
```

### Frontend Changes

#### api.js additions

```javascript
export async function getHistory() {
  const response = await fetch(`${API_BASE}/maps`)
  if (!response.ok) {
    throw new Error('Failed to get history')
  }
  return response.json()
}

export async function clearHistory() {
  const response = await fetch(`${API_BASE}/maps`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error('Failed to clear history')
  }
  return response.json()
}
```

#### App.vue changes

1. Change default: `dataSource: 'overture'`

2. Add history data:
```javascript
data() {
  return {
    // ... existing
    history: [],
    showHistory: false,
  }
}
```

3. Add methods:
```javascript
async loadHistory() {
  try {
    const result = await getHistory()
    this.history = result.jobs.filter(j => j.status === 'completed')
  } catch (err) {
    console.error('Failed to load history:', err)
  }
},

async clearAllHistory() {
  if (!confirm('Delete all generated maps? This cannot be undone.')) return
  try {
    await clearHistory()
    this.history = []
  } catch (err) {
    alert('Failed to clear history: ' + err.message)
  }
}
```

4. Add template section after results:
```vue
<!-- History -->
<section class="card history-card">
  <div class="history-header" @click="showHistory = !showHistory">
    <h2>History ({{ history.length }})</h2>
    <span class="toggle-icon">{{ showHistory ? '▼' : '►' }}</span>
  </div>

  <div v-if="showHistory" class="history-content">
    <div v-if="history.length === 0" class="empty-history">
      No maps generated yet
    </div>

    <div v-for="job in history" :key="job.job_id" class="history-item">
      <div class="history-info">
        <span class="history-location">{{ job.location_name }}</span>
        <span class="history-date">{{ formatDate(job.created_at) }}</span>
      </div>
      <div class="history-stats">
        <span>{{ job.file_info?.size_human }}</span>
        <span>{{ formatNumber(job.file_info?.triangles) }} triangles</span>
      </div>
      <a :href="getDownloadUrl(job.job_id, 'stl')" class="btn-small" download>
        Download
      </a>
    </div>

    <button v-if="history.length > 0" class="btn-danger" @click="clearAllHistory">
      Clear All History
    </button>
  </div>
</section>
```

## Acceptance Criteria

- [x] Data source defaults to "overture" instead of "osm"
- [x] History section shows list of completed jobs
- [x] Each history item shows: location, date, size, triangle count
- [x] Each history item has a download button
- [x] History is collapsible (collapsed by default)
- [x] "Clear All History" button deletes all jobs and files
- [x] Confirmation dialog before clearing history
- [x] History updates after generating a new map
- [x] Empty state shown when no history exists

## References

- Current App.vue: `frontend/src/App.vue:209` (dataSource default)
- Current API client: `frontend/src/api.js`
- Backend endpoints: `backend/main.py:137-296`
- Job status model: `backend/main.py:89-99`
