// MeterMate Custom Panel for Home Assistant
// Updated to use Home Assistant UI components

(function() {
  'use strict';

  // Load icon polyfill first
  const iconPolyfill = document.createElement('script');
  iconPolyfill.src = '/metermate/ha-icon-polyfill.js';
  document.head.appendChild(iconPolyfill);

  // Also load API for backward compatibility
  const apiScript = document.createElement('script');
  apiScript.src = '/metermate/api.js';
  document.head.appendChild(apiScript);

  // Import the modern HA UI version
  const script = document.createElement('script');
  script.type = 'module';
  script.src = '/metermate/ha-metermate-panel.js';
  document.head.appendChild(script);

  // Define the custom element that HA expects
  class MeterMatePanel extends HTMLElement {
    constructor() {
      super();
      this.hass = null;
      this.narrow = false;
      this.panel = null;
      this.route = null;
    }

    set hass(value) {
      this._hass = value;
      // Pass to the HA UI component when it's ready
      this._updateHAComponent();
    }

    get hass() {
      return this._hass;
    }

    set narrow(value) {
      this._narrow = value;
      this._updateHAComponent();
    }

    get narrow() {
      return this._narrow;
    }

    connectedCallback() {
      // Wait for the HA component to be available
      this._waitForHAComponent();
    }

    async _waitForHAComponent() {
      let attempts = 0;
      while (!customElements.get('ha-metermate-panel') && attempts < 50) {
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
      }
      this._createHAComponent();
    }

    _createHAComponent() {
      // Create the HA UI component
      const haComponent = document.createElement('ha-metermate-panel');
      haComponent.hass = this._hass;
      haComponent.narrow = this._narrow;
      haComponent.panel = this.panel;
      haComponent.route = this.route;

      this.appendChild(haComponent);
      this._haComponent = haComponent;
    }

    _updateHAComponent() {
      if (this._haComponent) {
        if (this._hass) this._haComponent.hass = this._hass;
        if (this._narrow !== undefined) this._haComponent.narrow = this._narrow;
      }
    }
  }

  // Register the panel element
  customElements.define('metermate-panel', MeterMatePanel);

})();
