/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class TTWizardFinishGeolocation extends Component {
    static template = "technician_task_mgmt.WizardFinishGeolocationButton";
    static props = {
        wizardId: Number,
        finishOption: String,
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.onClickConfirm = useDebounced(this.confirmTask, 200, { immediate: true });
    }

    async confirmTask() {
        console.log('Confirming task with geolocation...');

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
                            timeout: 5000,
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

            // Show a brief info message if geolocation was denied
            if (error.code === 1) { // PERMISSION_DENIED
                this.notification.add("Géolocalisation refusée - la tâche se terminera sans coordonnées GPS", {
                    type: "info",
                    duration: 3000
                });
            } else if (error.code === 2) { // POSITION_UNAVAILABLE
                this.notification.add("Position GPS indisponible - la tâche se terminera sans coordonnées", {
                    type: "info",
                    duration: 3000
                });
            } else if (error.code === 3) { // TIMEOUT
                this.notification.add("Délai de géolocalisation dépassé - la tâche se terminera sans coordonnées", {
                    type: "info",
                    duration: 3000
                });
            }
        }

        // Always finish the task, with or without coordinates
        console.log("Confirming wizard with ID:", this.props.wizardId, "latitude:", latitude, "longitude:", longitude);

        // Check if we have a valid wizard ID
        if (!this.props.wizardId || this.props.wizardId === 0) {
            console.error("Invalid wizard ID, cannot call RPC methods");
            this.notification.add("Géolocalisation " + (latitude ? "réussie" : "échouée") + ". Erreur technique - fermeture du wizard.", {
                type: "warning",
                duration: 3000
            });
            setTimeout(() => {
                this.actionService.doAction({'type': 'ir.actions.act_window_close'});
            }, 1500);
            return;
        }

        try {
            // First method: try with location
            const result = await this.orm.call("tt.task.finish.wizard", "action_confirm_with_location", [this.props.wizardId], {
                latitude: latitude,
                longitude: longitude
            });

            console.log("action_confirm_with_location result:", result);
            this._handleResult(result);

        } catch (error) {
            console.error("action_confirm_with_location failed:", error);

            // Check if it's a record not found error (wizard expired/deleted)
            if (error.message && error.message.includes('Record does not exist')) {
                console.log("Wizard record expired/deleted - wizard session timeout");

                // Show appropriate message
                if (latitude && longitude) {
                    this.notification.add("Géolocalisation réussie mais session expirée. Veuillez relancer l'action.", {
                        type: "warning",
                        duration: 4000
                    });
                } else {
                    this.notification.add("Session expirée. Veuillez relancer l'action.", {
                        type: "warning",
                        duration: 3000
                    });
                }

                // Close the wizard
                this.actionService.doAction({'type': 'ir.actions.act_window_close'});
                return;
            }

            console.log("Trying fallback action_confirm...");

            // Call the action_confirm method directly via ORM
            try {
                console.log("Calling action_confirm directly via ORM...");
                const fallbackResult = await this.orm.call("tt.task.finish.wizard", "action_confirm", [this.props.wizardId]);
                console.log("Direct action_confirm result:", fallbackResult);

                // Handle the result
                if (fallbackResult && fallbackResult.type === 'ir.actions.act_window_close') {
                    this.actionService.doAction(fallbackResult);
                } else {
                    // Default: close the wizard
                    this.actionService.doAction({'type': 'ir.actions.act_window_close'});
                }

            } catch (fallbackError) {
                console.error("Direct action_confirm also failed:", fallbackError);

                // Show informative message based on what we achieved
                if (latitude && longitude) {
                    this.notification.add("Géolocalisation réussie mais erreur de confirmation. Veuillez réessayer.", {
                        type: "warning",
                        duration: 4000
                    });
                } else {
                    this.notification.add("Géolocalisation échouée et erreur de confirmation. Veuillez réessayer.", {
                        type: "warning",
                        duration: 4000
                    });
                }

                // Close the wizard anyway
                setTimeout(() => {
                    this.actionService.doAction({'type': 'ir.actions.act_window_close'});
                }, 2000);
            }
        }
    }

    _handleResult(result) {
        if (result && result.success) {
            console.log('Task confirmed successfully');
            // Close the wizard
            if (result.action) {
                this.actionService.doAction(result.action);
            } else {
                this.actionService.doAction({'type': 'ir.actions.act_window_close'});
            }
        } else if (result && result.error) {
            this.notification.add(result.error, {type: "danger"});
        } else if (result && result.type === 'ir.actions.act_window_close') {
            // Handle fallback result
            console.log('Task confirmed successfully (fallback)');
            this.actionService.doAction(result);
        } else {
            // Close the wizard as default
            this.actionService.doAction({'type': 'ir.actions.act_window_close'});
        }
    }
}