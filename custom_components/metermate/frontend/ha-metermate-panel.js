// MeterMate Panel using Home Assistant UI Components
// Simplified version using available HA design system

// Simple base class for HA compatibility
class HAMeterMatePanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });

      // State properties
      this._hass = null;
      this._narrow = false;
      this._meters = [];
      this._readings = [];
      this._selectedMeter = null;
      this._loading = false;
      this._showAddDialog = false;
      this._showEditDialog = false;
      this._editingReading = null;
      this._alert = null;

      this._api = null;

      // Initialize
      this._initialize();
    }

    // Property setters/getters following HA conventions
    set hass(value) {
      this._hass = value;
      if (value && window.MeterMateAPI) {
        this._api = new window.MeterMateAPI.MeterMateAPI(value);
        this._loadData();
      }
      this._render();
    }

    get hass() {
      return this._hass;
    }

    set narrow(value) {
      this._narrow = value;
      this._render();
    }

    get narrow() {
      return this._narrow;
    }

    async _initialize() {
      // Wait for dependencies
      let attempts = 0;
      while (!window.MeterMateAPI && attempts < 50) {
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
      }

      if (this.hass && window.MeterMateAPI) {
        this._api = new window.MeterMateAPI.MeterMateAPI(this.hass);
        await this._loadData();
      }

      this._render();
    }

    async _loadData() {
      if (!this._api) return;

      this._loading = true;
      this._render();

      try {
        const [meters, readings] = await Promise.all([
          this._api.getMeters(),
          this._api.getReadings(),
        ]);

        this._meters = meters;
        this._readings = readings;

        // Auto-select first meter if none selected
        if (this._meters.length > 0 && !this._selectedMeter) {
          this._selectedMeter = this._meters[0].entity_id;
        }
      } catch (error) {
        console.error("MeterMate: Error loading data:", error);
        this._showAlert("error", "Failed to load data");
      } finally {
        this._loading = false;
        this._render();
      }
    }

    _showAlert(type, message) {
      this._alert = { type, message };
      this._render();
      setTimeout(() => {
        this._alert = null;
        this._render();
      }, type === "error" ? 5000 : 3000);
    }

    _getFilteredReadings() {
      if (!this._selectedMeter) return [];
      return this._readings
        .filter(reading => reading.meter_id === this._selectedMeter)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    }

    _formatDateTime(timestamp) {
      return new Date(timestamp).toLocaleString();
    }

    _formatValue(value, unit) {
      return `${value} ${unit || ""}`;
    }

    _handleMeterSelect(meterId) {
      this._selectedMeter = meterId;
      this._render();
    }

    async _refreshMeters() {
      console.log('Refreshing meters...');
      await this._loadData();
      this._showAlert("success", "Meters refreshed");
    }

    async _rebuildHistory() {
      if (!this._selectedMeter) {
        this._showAlert("error", "Please select a meter first");
        return;
      }

      const confirmed = confirm(
        "This will rebuild the historical data for the selected meter, " +
        "cleaning up any state journey and replacing it with proper historical records. " +
        "This action cannot be undone. Continue?"
      );

      if (!confirmed) {
        return;
      }

      try {
        console.log('Rebuilding history for:', this._selectedMeter);

        // Call the rebuild_history service
        await this._hass.callService("metermate", "rebuild_history", {
          entity_id: this._selectedMeter
        });

        this._showAlert("success", "History rebuilt successfully");

        // Refresh data to show updated state
        await this._loadData();

      } catch (error) {
        console.error('Error rebuilding history:', error);
        this._showAlert("error", `Failed to rebuild history: ${error.message}`);
      }
    }

    _openAddDialog() {
      this._showAddDialog = true;
      this._render();
    }

    _closeAddDialog() {
      this._showAddDialog = false;
      this._render();
    }

    _openEditDialog(reading) {
      this._editingReading = reading;
      this._showEditDialog = true;
      this._render();
    }

    _closeEditDialog() {
      this._showEditDialog = false;
      this._editingReading = null;
      this._render();
    }

    async _handleAddReading(event) {
      event.preventDefault();
      const formData = new FormData(event.target);
      const entryType = formData.get("entryType");

      if (!this._selectedMeter) {
        this._showAlert("error", "Please select a meter first");
        return;
      }

      try {
        if (entryType === "meter_reading") {
          // Handle meter reading entry
          const meterReading = parseFloat(formData.get("meter_reading"));
          const timestamp = formData.get("reading_datetime");
          const notes = formData.get("notes") || "";

          if (!meterReading || meterReading < 0) {
            this._showAlert("error", "Please enter a valid meter reading");
            return;
          }

          await this._api.callService("add_meter_reading", {
            entity_id: this._selectedMeter,
            meter_reading: meterReading,
            timestamp: new Date(timestamp).toISOString(),
            notes: notes
          });

          this._showAlert("success", "Meter reading added successfully");

        } else if (entryType === "consumption") {
          // Handle consumption period entry
          const consumption = parseFloat(formData.get("consumption"));
          const periodStart = formData.get("period_start");
          const periodEnd = formData.get("period_end");
          const notes = formData.get("notes") || "";

          if (!consumption || consumption < 0) {
            this._showAlert("error", "Please enter a valid consumption amount");
            return;
          }

          if (!periodStart || !periodEnd) {
            this._showAlert("error", "Please specify both period start and end dates");
            return;
          }

          if (new Date(periodStart) >= new Date(periodEnd)) {
            this._showAlert("error", "Period start must be before period end");
            return;
          }

          await this._api.callService("add_consumption_period", {
            entity_id: this._selectedMeter,
            consumption: consumption,
            period_start: new Date(periodStart).toISOString(),
            period_end: new Date(periodEnd).toISOString(),
            notes: notes
          });

          this._showAlert("success", "Consumption period added successfully");
        }

        this._closeAddDialog();
        await this._loadData();
      } catch (error) {
        console.error("MeterMate: Error adding reading:", error);
        this._showAlert("error", `Failed to add reading: ${error.message || error}`);
      }
    }

    _toggleEntryType() {
      const meterReadingFields = this.shadowRoot.getElementById("meter-reading-fields");
      const consumptionFields = this.shadowRoot.getElementById("consumption-fields");
      const entryType = this.shadowRoot.querySelector('input[name="entryType"]:checked').value;

      if (entryType === "meter_reading") {
        meterReadingFields.style.display = "block";
        consumptionFields.style.display = "none";
        // Make meter reading required
        this.shadowRoot.getElementById("add-meter-reading").required = true;
        this.shadowRoot.getElementById("add-consumption").required = false;
        this.shadowRoot.getElementById("add-period-start").required = false;
        this.shadowRoot.getElementById("add-period-end").required = false;
      } else {
        meterReadingFields.style.display = "none";
        consumptionFields.style.display = "block";
        // Make consumption fields required
        this.shadowRoot.getElementById("add-meter-reading").required = false;
        this.shadowRoot.getElementById("add-consumption").required = true;
        this.shadowRoot.getElementById("add-period-start").required = true;
        this.shadowRoot.getElementById("add-period-end").required = true;
      }
    }

    async _handleEditReading(event) {
      event.preventDefault();
      const formData = new FormData(event.target);

      if (!this._editingReading) return;

      try {
        await this._api.updateReading(
          this._editingReading.meter_id,
          this._editingReading.id,
          parseFloat(formData.get("value")),
          formData.get("datetime"),
          formData.get("notes") || ""
        );

        this._showAlert("success", "Reading updated successfully");
        this._closeEditDialog();
        await this._loadData();
      } catch (error) {
        console.error("MeterMate: Error updating reading:", error);
        this._showAlert("error", "Failed to update reading");
      }
    }

    async _handleDeleteReading(meterId, readingId) {
      const confirmed = confirm(
        "Are you sure you want to delete this reading? This action cannot be undone."
      );

      if (!confirmed) return;

      try {
        await this._api.deleteReading(meterId, readingId);
        this._showAlert("success", "Reading deleted successfully");
        await this._loadData();
      } catch (error) {
        console.error("MeterMate: Error deleting reading:", error);
        this._showAlert("error", "Failed to delete reading");
      }
    }

    _getStyles() {
      return `
        <style>
          :host {
            display: block;
            padding: 16px;
            background: var(--primary-background-color, #fafafa);
            color: var(--primary-text-color, #212121);
            min-height: 100vh;
            font-family: var(--paper-font-body1_-_font-family, "Roboto", "Noto", sans-serif);
          }

          .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding: 0 8px;
          }

          .header h1 {
            margin: 0;
            font-size: 32px;
            font-weight: 400;
            color: var(--primary-text-color, #212121);
            display: flex;
            align-items: center;
            gap: 12px;
          }

          .header ha-icon {
            --mdc-icon-size: 40px;
          }

          .content {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 24px;
            max-width: 1200px;
            margin: 0 auto;
          }

          .content.narrow {
            grid-template-columns: 1fr;
          }

          .card {
            background: var(--card-background-color, #fff);
            border-radius: var(--ha-card-border-radius, 8px);
            box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.1));
            overflow: hidden;
          }

          .card-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--divider-color, #e0e0e0);
          }

          .card-header h2 {
            margin: 0;
            font-size: 20px;
            font-weight: 500;
            color: var(--primary-text-color, #212121);
          }

          .card-content {
            padding: 16px 20px;
          }

          .empty-state {
            text-align: center;
            padding: 48px 24px;
            color: var(--secondary-text-color, #757575);
          }

          .empty-state ha-icon {
            font-size: 64px;
            opacity: 0.3;
            margin-bottom: 16px;
            display: block;
          }

          .meter-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
          }

          .meter-chip {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--chip-background-color, #f5f5f5);
            border: 2px solid transparent;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 14px;
            font-weight: 500;
          }

          .meter-chip:hover {
            background: var(--chip-background-color-hover, #eeeeee);
          }

          .meter-chip.selected {
            background: var(--primary-color, #1976d2);
            color: white;
            border-color: var(--primary-color, #1976d2);
          }

          .readings-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
          }

          .readings-table {
            width: 100%;
            border-collapse: collapse;
          }

          .readings-table th,
          .readings-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--divider-color, #e0e0e0);
          }

          .readings-table th {
            background: var(--table-header-background-color, #f5f5f5);
            font-weight: 500;
            color: var(--secondary-text-color, #757575);
          }

          .readings-table tr:hover {
            background: var(--table-row-background-color-hover, #f9f9f9);
          }

          .action-buttons {
            display: flex;
            gap: 8px;
          }

          .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
          }

          .btn-primary {
            background: var(--primary-color, #1976d2);
            color: white;
          }

          .btn-primary:hover {
            background: var(--primary-color-dark, #1565c0);
          }

          .btn-secondary {
            background: var(--secondary-color, #757575);
            color: white;
          }

          .btn-secondary:hover {
            background: var(--secondary-color-dark, #616161);
          }

          .btn-icon {
            padding: 8px;
            background: transparent;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            color: var(--secondary-text-color, #757575);
            transition: all 0.2s ease;
          }

          .btn-icon:hover {
            background: var(--divider-color, #e0e0e0);
          }

          .fab {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: var(--primary-color, #1976d2);
            color: white;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            transition: all 0.2s ease;
            z-index: 1000;
          }

          .fab:hover {
            background: var(--primary-color-dark, #1565c0);
            transform: scale(1.1);
          }

          .dialog-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
          }

          .dialog {
            background: var(--card-background-color, #fff);
            border-radius: 8px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            width: 90%;
            max-width: 500px;
            max-height: 90vh;
            overflow: auto;
          }

          .dialog-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--divider-color, #e0e0e0);
          }

          .dialog-header h3 {
            margin: 0;
            font-size: 20px;
            font-weight: 500;
          }

          .dialog-content {
            padding: 20px;
          }

          .dialog-actions {
            padding: 16px 20px;
            border-top: 1px solid var(--divider-color, #e0e0e0);
            display: flex;
            justify-content: flex-end;
            gap: 8px;
          }

          .form-field {
            margin-bottom: 16px;
          }

          .form-field label {
            display: block;
            margin-bottom: 4px;
            font-weight: 500;
            color: var(--primary-text-color, #212121);
          }

          .form-field input,
          .form-field textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid var(--divider-color, #e0e0e0);
            border-radius: 4px;
            font-size: 14px;
            font-family: inherit;
            box-sizing: border-box;
          }

          .form-field input:focus,
          .form-field textarea:focus {
            outline: none;
            border-color: var(--primary-color, #1976d2);
          }

          .loading-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 200px;
          }

          .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid var(--divider-color, #e0e0e0);
            border-top: 4px solid var(--primary-color, #1976d2);
            border-radius: 50%;
            animation: spin 1s linear infinite;
          }

          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }

          .alert {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 20px;
            border-radius: 4px;
            color: white;
            font-weight: 500;
            z-index: 3000;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
          }

          .alert.success {
            background: var(--success-color, #4caf50);
          }

          .alert.error {
            background: var(--error-color, #f44336);
          }

          ha-icon {
            display: inline-block;
            width: 24px;
            height: 24px;
          }

          @media (max-width: 768px) {
            :host {
              padding: 8px;
            }

            .content {
              grid-template-columns: 1fr;
              gap: 16px;
            }

            .header h1 {
              font-size: 24px;
            }

            .dialog {
              width: 95%;
            }
          }
        </style>
      `;
    }

    _render() {
      const readings = this._getFilteredReadings();

      this.shadowRoot.innerHTML = `
        ${this._getStyles()}

        ${this._alert ? `
          <div class="alert ${this._alert.type}">
            ${this._alert.message}
          </div>
        ` : ''}

        <div class="header">
          <h1>
            <ha-icon icon="mdi:meter-electric"></ha-icon>
            MeterMate
          </h1>
        </div>

        <div class="content ${this._narrow ? 'narrow' : ''}">
          ${this._renderMeterSelection()}
          ${this._renderReadingsSection(readings)}
        </div>

        ${this._selectedMeter ? `
          <button class="fab" onclick="window.meterMatePanel._openAddDialog()">
            <ha-icon icon="mdi:plus"></ha-icon>
          </button>
        ` : ''}

        ${this._showAddDialog ? this._renderAddDialog() : ''}
        ${this._showEditDialog ? this._renderEditDialog() : ''}
      `;

      // Store reference for event handlers
      window.meterMatePanel = this;
    }

    _renderMeterSelection() {
      return `
        <div class="card meter-selection">
          <div class="card-header">
            <h2>Meters</h2>
            <button class="refresh-btn" onclick="window.meterMatePanel._refreshMeters()" title="Refresh meters">
              <ha-icon icon="mdi:refresh"></ha-icon>
            </button>
            <button class="refresh-btn" onclick="window.meterMatePanel._rebuildHistory()" title="Rebuild History - Clean up state journey">
              <ha-icon icon="mdi:history"></ha-icon>
            </button>
          </div>
          <div class="card-content">
            ${this._loading ? `
              <div class="loading-container">
                <div class="spinner"></div>
              </div>
            ` : this._meters.length === 0 ? `
              <div class="empty-state">
                <ha-icon icon="mdi:meter-electric-outline"></ha-icon>
                <p>No meters found</p>
                <p>Configure meters in your Home Assistant configuration.</p>
                <button class="refresh-btn" onclick="window.meterMatePanel._refreshMeters()">
                  <ha-icon icon="mdi:refresh"></ha-icon>
                  Refresh
                </button>
              </div>
            ` : `
              <div class="meter-chips">
                ${this._meters.map(meter => `
                  <div class="meter-chip ${this._selectedMeter === meter.entity_id ? 'selected' : ''}"
                       onclick="window.meterMatePanel._handleMeterSelect('${meter.entity_id}')">
                    <ha-icon icon="${meter.icon || 'mdi:meter-electric'}"></ha-icon>
                    ${meter.name || meter.entity_id}
                  </div>
                `).join('')}
              </div>
            `}
          </div>
        </div>
      `;
    }

    _renderReadingsSection(readings) {
      return `
        <div class="card readings-section">
          <div class="card-header">
            <div class="readings-header">
              <h2>Recent Readings</h2>
              ${this._selectedMeter ? `
                <button class="btn btn-primary" onclick="window.meterMatePanel._openAddDialog()">
                  <ha-icon icon="mdi:plus"></ha-icon>
                  Add Reading
                </button>
              ` : ''}
            </div>
          </div>
          <div class="card-content">
            ${this._loading ? `
              <div class="loading-container">
                <div class="spinner"></div>
              </div>
            ` : !this._selectedMeter ? `
              <div class="empty-state">
                <ha-icon icon="mdi:selection-ellipse-arrow-inside"></ha-icon>
                <p>Select a meter to view readings</p>
              </div>
            ` : readings.length === 0 ? `
              <div class="empty-state">
                <ha-icon icon="mdi:chart-line-variant"></ha-icon>
                <p>No readings found</p>
                <p>Add your first reading to get started.</p>
              </div>
            ` : this._renderReadingsTable(readings)}
          </div>
        </div>
      `;
    }

    _renderReadingsTable(readings) {
      return `
        <table class="readings-table">
          <thead>
            <tr>
              <th>Period</th>
              <th>Meter Reading</th>
              <th>Consumption</th>
              <th>Notes</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${readings.map(reading => `
              <tr>
                <td>
                  ${reading.period_start && reading.period_end ?
                    `${this._formatDateTime(reading.period_start)} - ${this._formatDateTime(reading.period_end)}` :
                    this._formatDateTime(reading.timestamp)
                  }
                </td>
                <td>${this._formatValue(reading.value, reading.unit)}</td>
                <td>
                  ${reading.consumption ?
                    this._formatValue(reading.consumption, reading.unit) :
                    '-'
                  }
                </td>
                <td>${reading.notes || '-'}</td>
                <td class="action-buttons">
                  <button class="btn-icon" onclick="window.meterMatePanel._openEditDialog(${JSON.stringify(reading).replace(/"/g, '&quot;')})" title="Edit">
                    <ha-icon icon="mdi:pencil"></ha-icon>
                  </button>
                  <button class="btn-icon" onclick="window.meterMatePanel._handleDeleteReading('${reading.meter_id}', '${reading.id}')" title="Delete">
                    <ha-icon icon="mdi:delete"></ha-icon>
                  </button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    _renderAddDialog() {
      return `
        <div class="dialog-overlay" onclick="event.target === this && window.meterMatePanel._closeAddDialog()">
          <div class="dialog">
            <div class="dialog-header">
              <h3>Add New Reading</h3>
            </div>
            <form onsubmit="window.meterMatePanel._handleAddReading(event)">
              <div class="dialog-content">
                <!-- Entry Type Selection -->
                <div class="form-field">
                  <label>Entry Type</label>
                  <div class="radio-group">
                    <label class="radio-label">
                      <input type="radio" name="entryType" value="meter_reading" checked onchange="window.meterMatePanel._toggleEntryType()">
                      <span>Meter Reading</span>
                      <small>Enter the current meter reading (consumption will be calculated)</small>
                    </label>
                    <label class="radio-label">
                      <input type="radio" name="entryType" value="consumption" onchange="window.meterMatePanel._toggleEntryType()">
                      <span>Consumption Period</span>
                      <small>Enter consumption for a specific period (ending meter reading will be calculated)</small>
                    </label>
                  </div>
                </div>

                <!-- Meter Reading Fields -->
                <div id="meter-reading-fields">
                  <div class="form-field">
                    <label for="add-meter-reading">Meter Reading</label>
                    <input id="add-meter-reading" name="meter_reading" type="number" step="0.001" min="0">
                    <small>The current reading shown on your meter</small>
                  </div>
                  <div class="form-field">
                    <label for="add-reading-datetime">Reading Date & Time</label>
                    <input id="add-reading-datetime" name="reading_datetime" type="datetime-local" value="${new Date().toISOString().slice(0, 16)}">
                  </div>
                </div>

                <!-- Consumption Period Fields -->
                <div id="consumption-fields" style="display: none;">
                  <div class="form-field">
                    <label for="add-consumption">Consumption Amount</label>
                    <input id="add-consumption" name="consumption" type="number" step="0.001" min="0">
                    <small>Amount consumed during the period</small>
                  </div>
                  <div class="form-field-group">
                    <div class="form-field">
                      <label for="add-period-start">Period Start</label>
                      <input id="add-period-start" name="period_start" type="datetime-local">
                    </div>
                    <div class="form-field">
                      <label for="add-period-end">Period End</label>
                      <input id="add-period-end" name="period_end" type="datetime-local" value="${new Date().toISOString().slice(0, 16)}">
                    </div>
                  </div>
                </div>

                <!-- Common Fields -->
                <div class="form-field">
                  <label for="add-notes">Notes (optional)</label>
                  <input id="add-notes" name="notes" type="text" placeholder="e.g., Bill number, special circumstances">
                </div>
              </div>
              <div class="dialog-actions">
                <button type="button" class="btn btn-secondary" onclick="window.meterMatePanel._closeAddDialog()">Cancel</button>
                <button type="submit" class="btn btn-primary">Add Reading</button>
              </div>
            </form>
          </div>
        </div>
      `;
    }

    _renderEditDialog() {
      if (!this._editingReading) return '';

      return `
        <div class="dialog-overlay" onclick="event.target === this && window.meterMatePanel._closeEditDialog()">
          <div class="dialog">
            <div class="dialog-header">
              <h3>Edit Reading</h3>
            </div>
            <form onsubmit="window.meterMatePanel._handleEditReading(event)">
              <div class="dialog-content">
                <div class="form-field">
                  <label for="edit-value">Reading Value</label>
                  <input id="edit-value" name="value" type="number" step="0.01" value="${this._editingReading.value}" required autofocus>
                </div>
                <div class="form-field">
                  <label for="edit-datetime">Date & Time</label>
                  <input id="edit-datetime" name="datetime" type="datetime-local" value="${new Date(this._editingReading.timestamp).toISOString().slice(0, 16)}" required>
                </div>
                <div class="form-field">
                  <label for="edit-notes">Notes (optional)</label>
                  <input id="edit-notes" name="notes" type="text" value="${this._editingReading.notes || ''}">
                </div>
              </div>
              <div class="dialog-actions">
                <button type="button" class="btn btn-secondary" onclick="window.meterMatePanel._closeEditDialog()">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Reading</button>
              </div>
            </form>
          </div>
        </div>
      `;
    }
  }

  // Register the custom element
  customElements.define("ha-metermate-panel", HAMeterMatePanel);

  // Export for module loading
  window.HAMeterMatePanel = HAMeterMatePanel;
