/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

// Simple global function to handle geolocation
window.handleTaskGeolocation = function(action, taskId, wizardId = null) {
    console.log('handleTaskGeolocation called:', action, taskId, wizardId);

    function executeWithLocation(latitude = false, longitude = false) {
        if (action === 'start') {
            return rpc("/technician_task/start_with_location", {
                task_id: taskId,
                latitude: latitude,
                longitude: longitude,
            }).then(result => {
                if (result.success) {
                    window.location.reload();
                } else {
                    alert('Erreur: ' + (result.error || 'Impossible de démarrer la tâche'));
                }
            }).catch(error => {
                console.error('Error starting task:', error);
                alert('Erreur lors du démarrage de la tâche');
            });
        } else if (action === 'finish') {
            return rpc("/technician_task/finish_with_location", {
                task_id: taskId,
                option: 'done',
                latitude: latitude,
                longitude: longitude,
            }).then(result => {
                if (result.success) {
                    window.location.reload();
                } else {
                    alert('Erreur: ' + (result.error || 'Impossible de terminer la tâche'));
                }
            }).catch(error => {
                console.error('Error finishing task:', error);
                alert('Erreur lors de la finalisation de la tâche');
            });
        } else if (action === 'wizard' && wizardId) {
            return rpc("/technician_task/wizard_finish_with_location", {
                wizard_id: wizardId,
                latitude: latitude,
                longitude: longitude,
            }).then(result => {
                if (result.success) {
                    // Close wizard and reload parent
                    window.parent.location.reload();
                    if (window.parent && window.parent.jQuery) {
                        window.parent.jQuery('.modal').modal('hide');
                    }
                } else {
                    alert('Erreur: ' + (result.error || 'Impossible de terminer la tâche'));
                }
            }).catch(error => {
                console.error('Error finishing wizard:', error);
                alert('Erreur lors de la finalisation de la tâche');
            });
        }
    }

    // Try to get geolocation
    if (navigator.geolocation) {
        console.log('Requesting geolocation...');
        navigator.geolocation.getCurrentPosition(
            function(position) {
                console.log('Geolocation success:', position.coords.latitude, position.coords.longitude);
                executeWithLocation(position.coords.latitude, position.coords.longitude);
            },
            function(error) {
                console.log('Geolocation error:', error);
                // Fallback without location
                executeWithLocation();
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000
            }
        );
    } else {
        console.log('Geolocation not supported');
        // Fallback without location
        executeWithLocation();
    }
};