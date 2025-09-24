/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { WizardConfirmButton } from "./wizard_confirm_button";

export class WizardConfirmWidget extends Component {
    static template = "technician_task_mgmt.WizardConfirmWidget";
    static components = { WizardConfirmButton };

    get wizardId() {
        // Extract wizard ID from record
        let wizardId = this.props.record.resId || this.props.record.data.id || this.props.record.id;

        // Handle datapoint case
        if (typeof wizardId === 'string' && wizardId.startsWith('datapoint_')) {
            const extractedId = parseInt(wizardId.split('_').pop());
            if (!isNaN(extractedId)) {
                wizardId = extractedId;
            }
        }

        // Convert to number
        if (typeof wizardId === 'string' && !isNaN(parseInt(wizardId))) {
            wizardId = parseInt(wizardId);
        }

        return wizardId || 0;
    }

    get finishOption() {
        return this.props.record.data.finish_option || 'done';
    }

    get taskId() {
        // Get the actual task ID from the wizard
        return this.props.record.data.task_id && this.props.record.data.task_id[0] || false;
    }
}

registry.category("fields").add("wizard_confirm_geolocation", {
    component: WizardConfirmWidget,
});