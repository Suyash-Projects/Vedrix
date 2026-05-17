/**
 * OfflineQueue — Queues interview answers locally during WebSocket disconnects.
 *
 * Uses localStorage for persistence so answers survive page reloads.
 * Provides methods to enqueue, dequeue, and sync answers when reconnected.
 */

const QUEUE_KEY = 'vedrix_offline_queue';
const DRAFT_KEY = 'vedrix_interview_draft';

/**
 * Get the current queue of pending answers.
 * @returns {Array<{type: string, data: any, timestamp: number}>}
 */
export function getQueue() {
  try {
    const raw = localStorage.getItem(QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/**
 * Save the queue to localStorage.
 * @param {Array} queue
 */
function saveQueue(queue) {
  try {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  } catch {
    console.warn('Failed to save offline queue to localStorage');
  }
}

/**
 * Enqueue an answer for later delivery.
 * @param {string} type - Message type ('answer', 'code', etc.)
 * @param {any} data - The payload to send
 */
export function enqueueAnswer(type, data) {
  const queue = getQueue();
  queue.push({
    type,
    data,
    timestamp: Date.now(),
    id: crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`,
  });
  saveQueue(queue);
  return queue.length;
}

/**
 * Dequeue all pending answers.
 * @returns {Array} All queued items (queue is cleared after this call)
 */
export function dequeueAll() {
  const queue = getQueue();
  saveQueue([]);
  return queue;
}

/**
 * Get queue length.
 * @returns {number}
 */
export function getQueueLength() {
  return getQueue().length;
}

/**
 * Clear the entire queue.
 */
export function clearQueue() {
  saveQueue([]);
}

/**
 * Save current interview state as a draft.
 * @param {object} draft - { sessionId, currentQuestion, code, manualText, timeLeft, answers }
 */
export function saveDraft(draft) {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({
      ...draft,
      savedAt: Date.now(),
    }));
    return true;
  } catch {
    console.warn('Failed to save draft to localStorage');
    return false;
  }
}

/**
 * Load the last saved draft.
 * @returns {object|null}
 */
export function loadDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/**
 * Clear the saved draft.
 */
export function clearDraft() {
  localStorage.removeItem(DRAFT_KEY);
}

/**
 * Sync queued answers to the WebSocket connection.
 * @param {WebSocket} ws - The active WebSocket connection
 * @returns {Promise<{synced: number, failed: number}>}
 */
export async function syncQueue(ws) {
  const queue = dequeueAll();
  let synced = 0;
  let failed = 0;

  for (const item of queue) {
    try {
      if (ws.readyState === WebSocket.OPEN) {
        if (item.type === 'code') {
          ws.send(JSON.stringify({ type: item.type, data: item.data }));
        } else if (item.type === 'answer') {
          ws.send(JSON.stringify({ type: item.type, data: item.data }));
        }
        synced++;
      } else {
        failed++;
        // Re-enqueue if connection not ready
        enqueueAnswer(item.type, item.data);
      }
    } catch {
      failed++;
    }
  }

  return { synced, failed };
}
