export class EventSDK {
    constructor({ apiHost }) {
      this.apiHost = apiHost;
      this.queue = [];
      this.flushInterval = 5000;
      setInterval(() => this.flush(), this.flushInterval);
    }
  
    track(event, properties = {}, userId = null) {
      const payload = {
        event,
        user_id: userId,
        properties,
        timestamp: new Date().toISOString(),
        source: 'frontend',
      };
      this.queue.push(payload);
    }
  
    async flush() {
      if (!this.queue.length) return;
      const batch = this.queue.splice(0, this.queue.length);
      try {
        await fetch(\`\${this.apiHost}/collect\`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(batch),
        });
      } catch (err) {
        console.error('Failed to send events:', err);
        this.queue.unshift(...batch);
      }
    }
  }