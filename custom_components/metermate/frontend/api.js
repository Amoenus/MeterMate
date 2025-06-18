// MeterMate API Module
// Handles all Home Assistant service calls

window.MeterMateAPI = (function() {
  'use strict';

  class MeterMateAPI {
    constructor(hass) {
      this.hass = hass;
    }

    // Get all MeterMate sensors
    async getMeters() {
      if (!this.hass) {
        console.error('No hass available');
        return [];
      }

      console.log('Getting meters from entity registry...');

      try {
        // Get entity registry to identify MeterMate entities by their platform
        const entityRegistry = await this.hass.callWS({
          type: 'config/entity_registry/list'
        });

        console.log('Entity registry loaded, total entries:', entityRegistry.length);

        // Find entities that belong to the MeterMate integration
        const meterMateEntityIds = entityRegistry
          .filter(entity => {
            console.log(`Checking entity: ${entity.entity_id}, platform: ${entity.platform}`);
            return entity.platform === 'metermate';
          })
          .map(entity => entity.entity_id);

        console.log('MeterMate entity IDs from registry:', meterMateEntityIds);

        if (meterMateEntityIds.length === 0) {
          console.warn('No MeterMate entities found in registry');
          return [];
        }

        // Get current states for MeterMate entities
        const meterMateEntities = meterMateEntityIds
          .map(entityId => {
            const state = this.hass.states[entityId];
            if (!state) {
              console.warn(`No state found for entity: ${entityId}`);
              return null;
            }
            return state;
          })
          .filter(entity => entity && entity.entity_id.startsWith("sensor."));

        console.log('Filtered MeterMate entities:', meterMateEntities.map(e => e.entity_id));

        return meterMateEntities.map((entity) => ({
          entity_id: entity.entity_id,
          name: entity.attributes.friendly_name || entity.entity_id,
          state: entity.state,
          unit: entity.attributes.unit_of_measurement || "kWh",
          device_class: entity.attributes.device_class || "energy"
        }));
      } catch (error) {
        console.error('Error accessing entity registry:', error);
        throw error; // Re-throw to let the caller handle it
      }
    }

    // Get all readings (across all meters)
    async getReadings() {
      try {
        console.log('Getting readings...');
        // Get readings from all MeterMate sensors
        const meters = await this.getMeters();
        console.log('Found meters:', meters);
        const allReadings = [];

        for (const meter of meters) {
          try {
            console.log(`Calling get_readings service for ${meter.entity_id}...`);
            // Call service via callWS with return_response
            const result = await this.hass.callWS({
              type: "call_service",
              domain: "metermate",
              service: "get_readings",
              service_data: { entity_id: meter.entity_id },
              return_response: true,
            });
            console.log('Service result:', result);
            console.log('Service result type:', typeof result);
            console.log('Service result keys:', Object.keys(result || {}));

            // The WebSocket response might have the data in result.response or directly in result
            let readings = [];
            if (result?.response?.readings) {
              readings = result.response.readings;
            } else if (result?.readings) {
              readings = result.readings;
            } else if (Array.isArray(result)) {
              readings = result;
            } else {
              console.warn('Unexpected response structure:', result);
              readings = [];
            }

            console.log('Extracted readings:', readings);
            readings.forEach(reading => {
              reading.meter_id = meter.entity_id; // Add meter reference
            });
            allReadings.push(...readings);
          } catch (error) {
            console.warn(`Failed to get readings for ${meter.entity_id}:`, error);
          }
        }

        console.log('All readings:', allReadings);
        return allReadings;
      } catch (error) {
        console.error("Error loading readings:", error);
        throw error;
      }
    }

    // Get readings for a specific meter
    async getMeterReadings(entityId) {
      try {
        console.log(`Getting readings for meter: ${entityId}`);
        const result = await this.hass.callWS({
          type: "call_service",
          domain: "metermate",
          service: "get_readings",
          service_data: { entity_id: entityId },
          return_response: true,
        });
        console.log('Meter readings result:', result);
        console.log('Meter readings result type:', typeof result);
        console.log('Meter readings result keys:', Object.keys(result || {}));

        // Handle different possible response structures
        let readings = [];
        if (result?.response?.readings) {
          readings = result.response.readings;
        } else if (result?.readings) {
          readings = result.readings;
        } else if (Array.isArray(result)) {
          readings = result;
        } else {
          console.warn('Unexpected response structure:', result);
          readings = [];
        }

        return readings;
      } catch (error) {
        console.error("Error loading readings:", error);
        throw error;
      }
    }

    // Add a new reading
    async addReading(entityId, value, timestamp, notes) {
      try {
        await this.hass.callService("metermate", "add_reading", {
          entity_id: entityId,
          value: parseFloat(value),
          timestamp: timestamp || undefined,
          notes: notes || undefined
        });
      } catch (error) {
        console.error("Error adding reading:", error);
        throw error;
      }
    }

    // Update an existing reading
    async updateReading(entityId, readingId, value, timestamp, notes) {
      try {
        await this.hass.callService("metermate", "update_reading", {
          entity_id: entityId,
          reading_id: readingId,
          value: parseFloat(value),
          timestamp: timestamp || undefined,
          notes: notes || undefined
        });
      } catch (error) {
        console.error("Error updating reading:", error);
        throw error;
      }
    }

    // Delete a reading
    async deleteReading(entityId, readingId) {
      try {
        await this.hass.callService("metermate", "delete_reading", {
          entity_id: entityId,
          reading_id: readingId
        });
      } catch (error) {
        console.error("Error deleting reading:", error);
        throw error;
      }
    }

    // Generic service call method
    async callService(serviceName, serviceData) {
      try {
        console.log(`Calling MeterMate service: ${serviceName}`, serviceData);
        await this.hass.callService("metermate", serviceName, serviceData);
        console.log(`Service ${serviceName} completed successfully`);
      } catch (error) {
        console.error(`Error calling service ${serviceName}:`, error);
        throw error;
      }
    }
  }

  return {
    MeterMateAPI
  };
})();
