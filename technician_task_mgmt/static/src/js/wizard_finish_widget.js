/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { TTWizardFinishGeolocation } from "./wizard_finish_component";

export class TTWizardFinishWidget extends Component {
    static template = "technician_task_mgmt.WizardFinishFieldWidget";
    static components = { TTWizardFinishGeolocation };

    get wizardId() {
        console.log('wizardId value:', this.props.record.resId, 'type:', typeof this.props.record.resId);
        console.log('Full record:', this.props.record);
        console.log('Record data:', this.props.record.data);
        console.log('Record context:', this.props.record.context);
        console.log('Props:', this.props);

        // Try different ways to get the wizard ID
        let wizardId = this.props.record.resId ||
                      this.props.record.data.id ||
                      this.props.record.id ||
                      (this.props.record.context && this.props.record.context.active_id);

        // Handle datapoint case - extract numeric ID
        if (typeof wizardId === 'string' && wizardId.startsWith('datapoint_')) {
            const extractedId = parseInt(wizardId.split('_').pop());
            if (!isNaN(extractedId)) {
                wizardId = extractedId;
            }
        }

        // Convert to number if it's a string number
        if (typeof wizardId === 'string' && !isNaN(parseInt(wizardId))) {
            wizardId = parseInt(wizardId);
        }

        console.log('Final wizardId:', wizardId);
        return wizardId || 0;
    }

    get finishOption() {
        return this.props.record.data.finish_option || 'done';
    }
}

registry.category("fields").add("tt_wizard_finish_button", {
    component: TTWizardFinishWidget,
});