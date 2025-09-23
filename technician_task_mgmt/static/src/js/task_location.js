/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

/**
 * Utility functions for geolocation in technician tasks
 */
export class TaskLocationService {

    /**
     * Start a task with geolocation
     */
    static async startTaskWithLocation(taskId) {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                // Fallback to starting without location
                this.startTaskWithoutLocation(taskId).then(resolve).catch(reject);
                return;
            }

            navigator.geolocation.getCurrentPosition(
                async ({ coords: { latitude, longitude } }) => {
                    try {
                        const result = await rpc("/technician_task/start_with_location", {
                            task_id: taskId,
                            latitude,
                            longitude,
                        });
                        resolve(result);
                    } catch (error) {
                        reject(error);
                    }
                },
                async (error) => {
                    // Fallback to starting without GPS coordinates
                    try {
                        const result = await this.startTaskWithoutLocation(taskId);
                        resolve(result);
                    } catch (fallbackError) {
                        reject(fallbackError);
                    }
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000
                }
            );
        });
    }

    /**
     * Finish a task with geolocation
     */
    static async finishTaskWithLocation(taskId, option = 'done') {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                // Fallback to finishing without location
                this.finishTaskWithoutLocation(taskId, option).then(resolve).catch(reject);
                return;
            }

            navigator.geolocation.getCurrentPosition(
                async ({ coords: { latitude, longitude } }) => {
                    try {
                        const result = await rpc("/technician_task/finish_with_location", {
                            task_id: taskId,
                            option,
                            latitude,
                            longitude,
                        });
                        resolve(result);
                    } catch (error) {
                        reject(error);
                    }
                },
                async (error) => {
                    // Fallback to finishing without GPS coordinates
                    try {
                        const result = await this.finishTaskWithoutLocation(taskId, option);
                        resolve(result);
                    } catch (fallbackError) {
                        reject(fallbackError);
                    }
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000
                }
            );
        });
    }

    /**
     * Start task without geolocation (fallback)
     */
    static async startTaskWithoutLocation(taskId) {
        return rpc("/technician_task/start_with_location", {
            task_id: taskId
        });
    }

    /**
     * Finish task without geolocation (fallback)
     */
    static async finishTaskWithoutLocation(taskId, option = 'done') {
        return rpc("/technician_task/finish_with_location", {
            task_id: taskId,
            option
        });
    }

    /**
     * Finish wizard with geolocation
     */
    static async finishWizardWithLocation(wizardId) {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                // Fallback to finishing without location
                this.finishWizardWithoutLocation(wizardId).then(resolve).catch(reject);
                return;
            }

            navigator.geolocation.getCurrentPosition(
                async ({ coords: { latitude, longitude } }) => {
                    try {
                        const result = await rpc("/technician_task/wizard_finish_with_location", {
                            wizard_id: wizardId,
                            latitude,
                            longitude,
                        });
                        resolve(result);
                    } catch (error) {
                        reject(error);
                    }
                },
                async (error) => {
                    // Fallback to finishing without GPS coordinates
                    try {
                        const result = await this.finishWizardWithoutLocation(wizardId);
                        resolve(result);
                    } catch (fallbackError) {
                        reject(fallbackError);
                    }
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000
                }
            );
        });
    }

    /**
     * Finish wizard without geolocation (fallback)
     */
    static async finishWizardWithoutLocation(wizardId) {
        return rpc("/technician_task/wizard_finish_with_location", {
            wizard_id: wizardId
        });
    }
}