/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(FormController.prototype, {

    setup() {
        super.setup();
        this.notification = useService("notification");
        console.log('TTM FormController patch loaded!');
    },

    async executeButtonCallback(params) {
        const { name, resModel, resId } = params;
        console.log('Button clicked:', name, resModel, resId);

        // Intercept start button ONLY for geolocation
        if (resModel === 'tt.task' && resId && name === 'action_start_with_location') {
            console.log('Intercepting start button - requesting geolocation...');

            if (!navigator.geolocation) {
                console.log('Geolocation not supported, falling back');
                return rpc("/technician_task/start_with_location", {
                    task_id: resId
                }).then(result => {
                    if (result.success) {
                        return this.model.root.load().then(() => this.render());
                    } else {
                        this.notification.add(result.error || 'Failed to start task', { type: 'danger' });
                    }
                });
            }

            // Request geolocation using community-recommended method for Odoo 16+
            const self = this;

            function showPosition(position) {
                console.log('Geolocation success:', position.coords.latitude, position.coords.longitude);
                rpc("/technician_task/start_with_location", {
                    task_id: resId,
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                }).then(result => {
                    if (result.success) {
                        self.model.root.load().then(() => self.render());
                    } else {
                        self.notification.add(result.error || 'Failed to start task', { type: 'danger' });
                    }
                });
            }

            function showError(error) {
                console.log('Geolocation error:', error);
                self.notification.add('Localisation non disponible, utilisation de la localisation IP', { type: 'warning' });
                rpc("/technician_task/start_with_location", {
                    task_id: resId
                }).then(result => {
                    if (result.success) {
                        self.model.root.load().then(() => self.render());
                    } else {
                        self.notification.add(result.error || 'Failed to start task', { type: 'danger' });
                    }
                });
            }

            navigator.geolocation.getCurrentPosition(showPosition, showError, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000
            });

            // Don't call original method - we handled it
            return;
        }

        // Call original method for all other buttons
        return super.executeButtonCallback(params);
    }
});