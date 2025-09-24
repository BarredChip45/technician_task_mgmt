/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { TTTaskStartGeolocation } from "./task_start_component";

export class TTTaskStartWidget extends Component {
    static template = "technician_task_mgmt.TaskStartFieldWidget";
    static components = { TTTaskStartGeolocation };

    get taskId() {
        console.log('taskId value:', this.props.record.resId, 'type:', typeof this.props.record.resId);
        return this.props.record.resId || 0;
    }

    get taskName() {
        return this.props.record.data.name;
    }

    get canStart() {
        return this.props.record.data.can_start;
    }
}

registry.category("fields").add("tt_task_start_button", {
    component: TTTaskStartWidget,
});