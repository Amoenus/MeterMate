// Simple ha-icon polyfill for MeterMate
// Provides basic icon rendering when HA icons aren't available

(function() {
  'use strict';

  // Only create if ha-icon doesn't exist
  if (!customElements.get('ha-icon')) {
    class HAIcon extends HTMLElement {
      constructor() {
        super();
        this.attachShadow({ mode: 'open' });
      }

      static get observedAttributes() {
        return ['icon'];
      }

      connectedCallback() {
        this.render();
      }

      attributeChangedCallback() {
        this.render();
      }

      render() {
        const icon = this.getAttribute('icon') || '';
        const iconName = icon.replace('mdi:', '');

        // Basic icon mapping for common icons
        const iconMap = {
          'meter-electric': '⚡',
          'meter-electric-outline': '🔌',
          'plus': '+',
          'pencil': '✏️',
          'delete': '🗑️',
          'chart-line-variant': '📊',
          'selection-ellipse-arrow-inside': '👆',
          'check': '✓',
          'close': '✕',
          'alert': '⚠️',
          'information': 'ℹ️'
        };

        const iconChar = iconMap[iconName] || '●';

        this.shadowRoot.innerHTML = `
          <style>
            :host {
              display: inline-block;
              width: var(--mdc-icon-size, 24px);
              height: var(--mdc-icon-size, 24px);
              font-size: var(--mdc-icon-size, 24px);
              line-height: 1;
              text-align: center;
              color: currentColor;
            }
          </style>
          <span>${iconChar}</span>
        `;
      }
    }

    customElements.define('ha-icon', HAIcon);
  }
})();
