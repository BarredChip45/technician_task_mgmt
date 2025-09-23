/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class WizardGeolocationConfirmAction extends Component {
    static template = "technician_task_mgmt.WizardGeolocationAction";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");

        // Start the geolocation process immediately
        this.start();
    }

    async start() {
        const params = this.props.action.params || {};
        const wizardId = params.wizard_id;
        const finishOption = params.finish_option || 'done';

        console.log('Starting geolocation confirmation for wizard:', wizardId);

        let latitude = false;
        let longitude = false;

        // Try to get geolocation
        try {
            if (navigator.geolocation) {
                console.log('Requesting geolocation...');
                const position = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(
                        resolve,
                        reject,
                        {
                            enableHighAccuracy: true,
                            timeout: 10000,
                            maximumAge: 0
                        }
                    );
                });

                latitude = position.coords.latitude;
                longitude = position.coords.longitude;
                console.log("Geolocation success - Latitude:", latitude, "Longitude:", longitude);
            } else {
                console.log("Geolocation not supported by browser");
            }
        } catch (error) {
            console.log("Geolocation failed or denied:", error.message);

            // Show brief notification for permission denied
            if (error.code === 1) { // PERMISSION_DENIED
                this.notification.add("Géolocalisation refusée - la tâche se terminera sans coordonnées GPS", {
                    type: "info",
                    duration: 3000
                });
            }
        }

        // Always confirm the task, with or without coordinates
        try {
            const result = await this.orm.call("tt.task.finish.wizard", "action_confirm_with_location", [wizardId], {
                latitude: latitude,
                longitude: longitude
            });

            console.log("Confirmation result:", result);

            if (result && result.success) {
                if (result.action) {
                    this.actionService.doAction(result.action);
                } else {
                    this.actionService.doAction({'type': 'ir.actions.act_window_close'});
                }
            } else if (result && result.error) {
                this.notification.add(result.error, {type: "danger"});
                this.actionService.doAction({'type': 'ir.actions.act_window_close'});
            } else {
                this.actionService.doAction({'type': 'ir.actions.act_window_close'});
            }

        } catch (error) {
            console.error("Failed to confirm wizard:", error);
            this.notification.add("Erreur lors de la confirmation: " + error.message, {type: "danger"});
            this.actionService.doAction({'type': 'ir.actions.act_window_close'});
        }
    }
}

registry.category("actions").add("tt_wizard_geolocation_confirm", WizardGeolocationConfirmAction);