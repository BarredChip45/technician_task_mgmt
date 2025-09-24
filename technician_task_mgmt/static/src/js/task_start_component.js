/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class TTTaskStartGeolocation extends Component {
    static template = "technician_task_mgmt.TaskStartGeolocationButton";
    static props = {
        taskId: Number,
        taskName: String,
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.onClickStart = useDebounced(this.startTask, 200, { immediate: true });
    }

    async startTask() {
        console.log('Starting task with geolocation...');

        let latitude = false;
        let longitude = false;

        // Try to get geolocation, but don't block if it fails
        try {
            if (navigator.geolocation) {
                const position = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(
                        resolve,
                        reject,
                        {
                            enableHighAccuracy: true,
                            timeout: 5000,  // Reduced timeout
                            maximumAge: 300000  // 5 minutes cache
                        }
                    );
                });

                latitude = position.coords.latitude;
                longitude = position.coords.longitude;
                console.log("Geolocation success - Latitude: " + latitude + " | Longitude: " + longitude);
            } else {
                console.log("Geolocation not supported by browser");
            }
        } catch (error) {
            console.log("Geolocation failed or denied:", error.message);
            // Continue without geolocation - this is normal behavior
        }

        // Always start the task, with or without coordinates
        try {
            const result = await this.orm.call("tt.task", "start_with_location_rpc", [this.props.taskId], {
                latitude: latitude,
                longitude: longitude
            });

            this._handleResult(result);
        } catch (error) {
            console.error("Failed to start task:", error);
        }
    }

    _handleResult(result) {
        if (result.success) {
            console.log('Task started successfully');
            // Trigger a soft reload by reloading the current record
            setTimeout(() => {
                location.reload();
            }, 100);
        } else if (result.error) {
            console.error('Task start error:', result.error);
        }
    }
}