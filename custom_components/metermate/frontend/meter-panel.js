// MeterMate Panel Main Logic
// Core panel functionality

window.MeterMatePanel = (function() {
  'use strict';

  class MeterMatePanel extends HTMLElement {
    constructor() {
      super();
      this.hass = null;
      this.narrow = false;
      this.panel = null;
      this.route = null;

      // Internal state
      this._meters = [];
      this._readings = [];
      this._selectedMeter = null;
      this._showAddForm = false;
      this._showEditForm = false;
      this._editingReading = null;
      this._loading = false;

      // Create shadow DOM
      this.attachShadow({ mode: 'open' });

      // Initialize
      this._initialize();
    }

    static get observedAttributes() {
      return ['narrow'];
    }

    attributeChangedCallback(name, oldValue, newValue) {
      if (name === 'narrow') {
        this.narrow = newValue !== null;
        this._render();
      }
    }

    set hass(value) {
      this._hass = value;
      if (value) {
        this._api = new window.MeterMateAPI.MeterMateAPI(value);
        this._loadData();
      }
    }

    get hass() {
      return this._hass;
    }

    async _initialize() {
      // Wait for dependencies to load
      let attempts = 0;
      while ((!window.MeterMateAPI || !window.MeterMateUI) && attempts < 50) {
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
      }

      if (!window.MeterMateAPI || !window.MeterMateUI) {
        console.error('MeterMate: Failed to load dependencies');
        return;
      }

      this._render();
    }

    async _loadData() {
      if (!this._api) return;

      this._loading = true;
      this._render();

      try {
        this._meters = await this._api.getMeters();
        this._readings = await this._api.getReadings();

        // Select first meter if none selected
        if (this._meters.length > 0 && !this._selectedMeter) {
          this._selectedMeter = this._meters[0].entity_id;
        }
      } catch (error) {
        console.error('MeterMate: Error loading data:', error);
        this._showError('Failed to load data');
      } finally {
        this._loading = false;
        this._render();
      }
    }

    _getFilteredReadings() {
      if (!this._selectedMeter) return [];
      return this._readings.filter(reading => reading.meter_id === this._selectedMeter);
    }

    _showError(message) {
      const toast = document.createElement('div');
      toast.className = 'toast error';
      toast.textContent = message;
      document.body.appendChild(toast);

      setTimeout(() => {
        toast.remove();
      }, 5000);
    }

    _showSuccess(message) {
      const toast = document.createElement('div');
      toast.className = 'toast success';
      toast.textContent = message;
      document.body.appendChild(toast);

      setTimeout(() => {
        toast.remove();
      }, 3000);
    }

    async _handleAddReading(event) {
      event.preventDefault();
      const formData = new FormData(event.target);

      if (!this._selectedMeter) {
        this._showError('Please select a meter first');
        return;
      }

      try {
        await this._api.addReading(
          this._selectedMeter,
          parseFloat(formData.get('value')),
          formData.get('datetime'),
          formData.get('notes') || ''
        );

        this._showSuccess('Reading added successfully');
        this._showAddForm = false;
        await this._loadData();
      } catch (error) {
        console.error('MeterMate: Error adding reading:', error);
        this._showError('Failed to add reading');
      }
    }

    async _handleEditReading(event) {
      event.preventDefault();
      const formData = new FormData(event.target);

      if (!this._editingReading) return;

      try {
        await this._api.updateReading(
          this._editingReading.id,
          parseFloat(formData.get('value')),
          formData.get('datetime'),
          formData.get('notes') || ''
        );

        this._showSuccess('Reading updated successfully');
        this._showEditForm = false;
        this._editingReading = null;
        await this._loadData();
      } catch (error) {
        console.error('MeterMate: Error updating reading:', error);
        this._showError('Failed to update reading');
      }
    }

    async _handleDeleteReading(readingId) {
      if (!confirm('Are you sure you want to delete this reading?')) {
        return;
      }

      try {
        await this._api.deleteReading(readingId);
        this._showSuccess('Reading deleted successfully');
        await this._loadData();
      } catch (error) {
        console.error('MeterMate: Error deleting reading:', error);
        this._showError('Failed to delete reading');
      }
    }

    _startEditReading(reading) {
      this._editingReading = reading;
      this._showEditForm = true;
      this._showAddForm = false;
      this._render();
    }

    _cancelEdit() {
      this._editingReading = null;
      this._showEditForm = false;
      this._render();
    }

    _toggleAddForm() {
      this._showAddForm = !this._showAddForm;
      this._showEditForm = false;
      this._editingReading = null;
      this._render();
    }

    _onMeterChange(event) {
      this._selectedMeter = event.target.value;
      this._render();
    }

    _render() {
      if (!this.shadowRoot) return;

      const ui = window.MeterMateUI;
      if (!ui) {
        this.shadowRoot.innerHTML = '<div>Loading dependencies...</div>';
        return;
      }

      // Main container
      const container = document.createElement('div');
      container.className = 'metermate-panel';

      // Header
      const header = ui.UIComponents.createHeader('MeterMate');
      container.appendChild(header);

      // Debug info
      const debugInfo = document.createElement('div');
      debugInfo.style.backgroundColor = '#f0f0f0';
      debugInfo.style.padding = '10px';
      debugInfo.style.marginBottom = '10px';
      debugInfo.style.fontFamily = 'monospace';
      debugInfo.style.fontSize = '12px';
      debugInfo.innerHTML = `
        <strong>Main Debug Info:</strong><br>
        Found Meters: ${this._meters.length}<br>
        Selected Meter: ${this._selectedMeter}<br>
        Meters: ${JSON.stringify(this._meters, null, 2)}
      `;
      container.appendChild(debugInfo);

      if (this._loading) {
        const loader = ui.UIComponents.createLoader();
        container.appendChild(loader);
        this.shadowRoot.innerHTML = '';
        this.shadowRoot.appendChild(container);
        return;
      }

      // Meter selector
      if (this._meters.length > 0) {
        const selectorContainer = document.createElement('div');
        selectorContainer.className = 'meter-selector';

        const label = document.createElement('label');
        label.textContent = 'Select Meter:';
        selectorContainer.appendChild(label);

        const meterOptions = this._meters.map(meter => ({
          value: meter.entity_id,
          text: meter.name
        }));

        const selector = ui.UIComponents.createSelect('meter', meterOptions);
        selector.value = this._selectedMeter || '';
        selector.addEventListener('change', (e) => this._onMeterChange(e));
        selectorContainer.appendChild(selector);

        container.appendChild(selectorContainer);
      }

      // Action buttons
      const actionBar = document.createElement('div');
      actionBar.className = 'action-bar';

      const addBtn = ui.UIComponents.createButton('Add Reading', 'primary', () => this._toggleAddForm());
      actionBar.appendChild(addBtn);

      const refreshBtn = ui.UIComponents.createButton('Refresh', 'secondary', () => this._loadData());
      actionBar.appendChild(refreshBtn);

      container.appendChild(actionBar);

      // Add form
      if (this._showAddForm) {
        const form = this._createAddForm();
        container.appendChild(form);
      }

      // Edit form
      if (this._showEditForm && this._editingReading) {
        const form = this._createEditForm();
        container.appendChild(form);
      }

      // Readings table
      if (this._selectedMeter) {
        const readingsContainer = this._createReadingsTable();
        container.appendChild(readingsContainer);
      }

      // Apply styles
      const styles = document.createElement('link');
      styles.rel = 'stylesheet';
      styles.href = '/local/metermate/styles.css';

      this.shadowRoot.innerHTML = '';
      this.shadowRoot.appendChild(styles);
      this.shadowRoot.appendChild(container);
    }

    _createAddForm() {
      const ui = window.MeterMateUI.UIComponents;

      const formContainer = document.createElement('div');
      formContainer.className = 'form-container';

      const form = document.createElement('form');
      form.addEventListener('submit', (e) => this._handleAddReading(e));

      // Form title
      const title = document.createElement('h3');
      title.textContent = 'Add New Reading';
      form.appendChild(title);

      // Value input
      const valueInput = ui.createInput('number', 'value', 'Reading value', true);
      valueInput.step = '0.001';
      form.appendChild(ui.createFormGroup('Value:', valueInput));

      // Datetime input
      const now = new Date();
      const datetimeInput = ui.createInput('datetime-local', 'datetime', '', true);
      datetimeInput.value = now.toISOString().slice(0, 16);
      form.appendChild(ui.createFormGroup('Date & Time:', datetimeInput));

      // Notes input
      const notesInput = document.createElement('textarea');
      notesInput.name = 'notes';
      notesInput.placeholder = 'Optional notes';
      notesInput.rows = 3;
      form.appendChild(ui.createFormGroup('Notes:', notesInput));

      // Buttons
      const buttonContainer = document.createElement('div');
      buttonContainer.className = 'form-buttons';

      const submitBtn = ui.createButton('Add Reading', 'primary');
      submitBtn.type = 'submit';
      buttonContainer.appendChild(submitBtn);

      const cancelBtn = ui.createButton('Cancel', 'secondary', () => this._toggleAddForm());
      buttonContainer.appendChild(cancelBtn);

      form.appendChild(buttonContainer);
      formContainer.appendChild(form);

      return formContainer;
    }

    _createEditForm() {
      const ui = window.MeterMateUI.UIComponents;

      const formContainer = document.createElement('div');
      formContainer.className = 'form-container';

      const form = document.createElement('form');
      form.addEventListener('submit', (e) => this._handleEditReading(e));

      // Form title
      const title = document.createElement('h3');
      title.textContent = 'Edit Reading';
      form.appendChild(title);

      // Value input
      const valueInput = ui.createInput('number', 'value', 'Reading value', true);
      valueInput.step = '0.001';
      valueInput.value = this._editingReading.value;
      form.appendChild(ui.createFormGroup('Value:', valueInput));

      // Datetime input
      const datetimeInput = ui.createInput('datetime-local', 'datetime', '', true);
      datetimeInput.value = new Date(this._editingReading.timestamp).toISOString().slice(0, 16);
      form.appendChild(ui.createFormGroup('Date & Time:', datetimeInput));

      // Notes input
      const notesInput = document.createElement('textarea');
      notesInput.name = 'notes';
      notesInput.placeholder = 'Optional notes';
      notesInput.rows = 3;
      notesInput.value = this._editingReading.notes || '';
      form.appendChild(ui.createFormGroup('Notes:', notesInput));

      // Buttons
      const buttonContainer = document.createElement('div');
      buttonContainer.className = 'form-buttons';

      const submitBtn = ui.createButton('Update Reading', 'primary');
      submitBtn.type = 'submit';
      buttonContainer.appendChild(submitBtn);

      const cancelBtn = ui.createButton('Cancel', 'secondary', () => this._cancelEdit());
      buttonContainer.appendChild(cancelBtn);

      form.appendChild(buttonContainer);
      formContainer.appendChild(form);

      return formContainer;
    }

    _createReadingsTable() {
      const ui = window.MeterMateUI.UIComponents;
      const readings = this._getFilteredReadings();

      const container = document.createElement('div');
      container.className = 'readings-container';

      const title = document.createElement('h3');
      title.textContent = 'Recent Readings';
      container.appendChild(title);

      // Debug information
      const debugInfo = document.createElement('div');
      debugInfo.style.backgroundColor = '#f0f0f0';
      debugInfo.style.padding = '10px';
      debugInfo.style.marginBottom = '10px';
      debugInfo.style.fontFamily = 'monospace';
      debugInfo.style.fontSize = '12px';
      debugInfo.innerHTML = `
        <strong>Debug Info:</strong><br>
        Selected Meter: ${this._selectedMeter}<br>
        Total Readings: ${this._readings.length}<br>
        Filtered Readings: ${readings.length}<br>
        Readings: ${JSON.stringify(this._readings, null, 2)}
      `;
      container.appendChild(debugInfo);

      if (readings.length === 0) {
        const emptyMsg = document.createElement('p');
        emptyMsg.className = 'empty-message';
        emptyMsg.textContent = 'No readings found for this meter.';
        container.appendChild(emptyMsg);
        return container;
      }

      const table = ui.createTable(
        ['Date', 'Value', 'Notes', 'Actions'],
        readings.map(reading => [
          new Date(reading.timestamp).toLocaleString(),
          `${reading.value} ${this._getSelectedMeterUnit()}`,
          reading.notes || '-',
          this._createReadingActions(reading)
        ])
      );

      container.appendChild(table);
      return container;
    }

    _createReadingActions(reading) {
      const ui = window.MeterMateUI.UIComponents;

      const actionsContainer = document.createElement('div');
      actionsContainer.className = 'reading-actions';

      const editBtn = ui.createButton('Edit', 'small', () => this._startEditReading(reading));
      const deleteBtn = ui.createButton('Delete', 'small danger', () => this._handleDeleteReading(reading.id));

      actionsContainer.appendChild(editBtn);
      actionsContainer.appendChild(deleteBtn);

      return actionsContainer;
    }

    _getSelectedMeterUnit() {
      if (!this._selectedMeter) return '';
      const meter = this._meters.find(m => m.entity_id === this._selectedMeter);
      return meter ? meter.unit : '';
    }
  }

  // Register the custom element
  customElements.define('metermate-panel', MeterMatePanel);

  return {
    MeterMatePanel
  };
})();
