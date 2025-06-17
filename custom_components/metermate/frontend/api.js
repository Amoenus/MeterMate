// MeterMate API Module
// Handles all Home Assistant service calls

window.MeterMateAPI = (function() {
  'use strict';

  class MeterMateAPI {
    constructor(hass) {
      this.hass = hass;
    }

    // Get all MeterMate sensors
    getMeters() {
      if (!this.hass || !this.hass.states) {
        return [];
      }

      const entities = Object.values(this.hass.states).filter(
        (entity) => entity.entity_id.startsWith("sensor.metermate_") ||
                   entity.entity_id.includes("manual_meter")
      );

      return entities.map((entity) => ({
        entity_id: entity.entity_id,
        name: entity.attributes.friendly_name || entity.entity_id,
        state: entity.state,
        unit: entity.attributes.unit_of_measurement || "kWh",
        device_class: entity.attributes.device_class || "energy"
      }));
    }

    // Get all readings (across all meters)
    async getReadings() {
      try {
        console.log('Getting readings...');
        // Get readings from all MeterMate sensors
        const meters = this.getMeters();
        console.log('Found meters:', meters);
        const allReadings = [];

        for (const meter of meters) {
          try {
            console.log(`Calling get_readings service for ${meter.entity_id}...`);
            const result = await this.hass.callService("metermate", "get_readings", {
              entity_id: meter.entity_id
            });
            console.log('Service result:', result);
            const readings = result?.readings || [];
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
        const result = await this.hass.callService("metermate", "get_readings", {
          entity_id: entityId
        });
        console.log('Meter readings result:', result);
        return result?.readings || [];
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
          reading_type: "cumulative",
          notes: notes || undefined
        });
      } catch (error) {
        console.error("Error adding reading:", error);
        throw error;
      }
    }

    // Update an existing reading
    async updateReading(readingId, value, timestamp, notes) {
      try {
        await this.hass.callService("metermate", "update_reading", {
          reading_id: readingId,
          value: parseFloat(value),
          timestamp: timestamp || undefined,
          reading_type: "cumulative",
          notes: notes || undefined
        });
      } catch (error) {
        console.error("Error updating reading:", error);
        throw error;
      }
    }

    // Delete a reading
    async deleteReading(readingId) {
      try {
        await this.hass.callService("metermate", "delete_reading", {
          reading_id: readingId
        });
      } catch (error) {
        console.error("Error deleting reading:", error);
        throw error;
      }
    }
  }

  return {
    MeterMateAPI
  };
})();
