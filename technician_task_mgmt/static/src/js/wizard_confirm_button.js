/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class WizardConfirmButton extends Component {
    static template = "technician_task_mgmt.WizardConfirmButton";
    static props = {
        taskId: Number,
        finishOption: String,
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.onClickConfirm = useDebounced(this.confirmTask, 200, { immediate: true });
    }

    async confirmTask() {
        console.log('Confirm button clicked, requesting geolocation...');

        // Request geolocation exactly like hr_attendance - update position then do action
        navigator.geolocation.getCurrentPosition(
            async ({coords: {latitude, longitude}}) => {
                console.log("Got location:", latitude, longitude);
                // Update task location like hr_attendance does with update_last_position
                await this.orm.call("tt.task", "update_end_location", [
                    [this.props.taskId],
                    latitude,
                    longitude
                ]);

                // Then do the main action
                const result = await this.orm.call("tt.task", "finish_task_from_wizard", [
                    [this.props.taskId],
                    this.props.finishOption,
                ]);
                this._handleResult(result);
            },
            async err => {
                console.log("No location:", err.message);
                // Update with false values like hr_attendance
                await this.orm.call("tt.task", "update_end_location", [
                    [this.props.taskId],
                    false,
                    false
                ]);

                // Then do the main action
                const result = await this.orm.call("tt.task", "finish_task_from_wizard", [
                    [this.props.taskId],
                    this.props.finishOption,
                ]);
                this._handleResult(result);
            }
        );
    }

    _handleResult(result) {
        // Handle result like hr_attendance
        if (result && result.action) {
            this.actionService.doAction(result.action);
        } else if (result && result.warning) {
            this.notification.add(result.warning, {type: "danger"});
        } else if (result && result.type === 'ir.actions.act_window_close') {
            this.actionService.doAction(result);
        } else {
            this.actionService.doAction({'type': 'ir.actions.act_window_close'});
        }
    }
}