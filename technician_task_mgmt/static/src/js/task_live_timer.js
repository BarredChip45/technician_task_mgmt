/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillUnmount } from "@odoo/owl";

// Live-ticking timer field. Reuses the same fields as the server-side
// _compute_current_timer_display so the display matches after a reload,
// but refreshes every second on the client for a live stopwatch.
export class TTLiveTimer extends Component {
    static template = "technician_task_mgmt.LiveTimer";
    static props = ["*"];

    setup() {
        this.state = useState({ display: this._compute() });
        this.interval = setInterval(() => {
            this.state.display = this._compute();
        }, 1000);
        onWillUnmount(() => clearInterval(this.interval));
    }

    _format(totalSeconds) {
        totalSeconds = Math.max(Math.floor(totalSeconds), 0);
        const h = Math.floor(totalSeconds / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        const s = totalSeconds % 60;
        const pad = (n) => String(n).padStart(2, "0");
        return `${pad(h)}:${pad(m)}:${pad(s)}`;
    }

    // Datetime fields arrive as luxon DateTime objects (or false). toMillis()
    // gives a correct epoch value regardless of the user timezone.
    _millis(value) {
        return value ? value.toMillis() : false;
    }

    // Frozen total duration (across all sessions), used whenever no timer is
    // actively running (draft, done, or "finished for today").
    _frozen(data) {
        const secs = (data.duration_hours || 0) * 3600;
        return secs > 0 ? this._format(secs) : "";
    }

    _compute() {
        const data = this.props.record.data;

        // Only tick while a timer line is actually open. can_stop is true when
        // running and not paused; can_resume is true when running and paused.
        // "Finished for today" keeps the task in_progress but closes the line,
        // so both are false there and the timer must stop.
        const running = data.can_stop || data.can_resume;
        if (!running) {
            return this._frozen(data);
        }

        const start = this._millis(data.start_datetime);
        if (!start) {
            return this._frozen(data);
        }
        const now = Date.now();
        let elapsed = (now - start) / 1000;
        let paused = data.accumulated_pause_seconds || 0;
        const pauseStart = this._millis(data.pause_start_datetime);
        if (pauseStart) {
            // While paused, elapsed and paused grow together → display freezes.
            paused += (now - pauseStart) / 1000;
        }
        return this._format(elapsed - paused);
    }

    get display() {
        return this.state.display;
    }
}

registry.category("fields").add("tt_live_timer", {
    component: TTLiveTimer,
});
