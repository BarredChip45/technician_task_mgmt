/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

// Patch the FormController to intercept button clicks on wizard
patch(FormController.prototype, {

    executeButtonCallback(clickParams) {
        console.log('executeButtonCallback called:', clickParams.name, this.props.resModel);

        // Simple: intercept only wizard confirm button
        if (clickParams.name === 'action_confirm' && this.props.resModel === 'tt.task.finish.wizard') {
            console.log('Wizard confirm intercepted! Requesting geolocation...');

            // Force geolocation request like hr_attendance
            if (navigator.geolocation) {
                console.log('navigator.geolocation available, calling getCurrentPosition...');
                navigator.geolocation.getCurrentPosition(
                ({coords: {latitude, longitude}}) => {
                    console.log("Got location:", latitude, longitude);
                    // Add location to context and call original method
                    const modifiedClickParams = {
                        ...clickParams,
                        context: {
                            ...clickParams.context,
                            end_latitude: latitude,
                            end_longitude: longitude
                        }
                    };
                    super.executeButtonCallback(modifiedClickParams);
                },
                err => {
                    console.log("Geolocation error:", err.message, err.code);
                    // Continue without location
                    const modifiedClickParams = {
                        ...clickParams,
                        context: {
                            ...clickParams.context,
                            end_latitude: false,
                            end_longitude: false
                        }
                    };
                    super.executeButtonCallback(modifiedClickParams);
                }
                );
            } else {
                console.log('navigator.geolocation NOT available');
                // Continue without location
                const modifiedClickParams = {
                    ...clickParams,
                    context: {
                        ...clickParams.context,
                        end_latitude: false,
                        end_longitude: false
                    }
                };
                super.executeButtonCallback(modifiedClickParams);
            }
            // Don't call super here - it will be called in the callbacks above
            return;
        }

        // For all other buttons, call the original method
        return super.executeButtonCallback(clickParams);
    }
});