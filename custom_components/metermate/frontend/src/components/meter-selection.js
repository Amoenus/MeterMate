// MeterMate Meter Selection Component
// Handles the display and interaction with meter selection

class MeterSelection {
  /**
   * Renders the meter selection component
   * @param {Object} options - Options for rendering
   * @param {Array} options.meters - Array of meter objects
   * @param {boolean} options.loading - Whether data is loading
   * @param {string} options.selectedMeter - Currently selected meter entity_id
   * @param {Function} options.onMeterSelect - Callback for meter selection
   * @param {Function} options.onRefreshMeters - Callback for refresh action
   * @param {Function} options.onRebuildHistory - Callback for rebuild history action
   * @returns {string} HTML string for the meter selection component
   */
  static render(options) {
    const {
      meters = [],
      loading = false,
      selectedMeter = null,
      onMeterSelect = () => {},
      onRefreshMeters = () => {},
      onRebuildHistory = () => {}
    } = options;

    return `
      <div class="card meter-selection">
        <div class="card-header">
          <h2>Meters</h2>
          <button class="refresh-btn" onclick="window.meterMatePanel._refreshMeters()" title="Refresh meters">
            <ha-icon icon="mdi:refresh"></ha-icon>
          </button>
          <button class="refresh-btn" onclick="window.meterMatePanel._rebuildHistory()" title="Rebuild History - Calculate consumption and clean up data">
            <ha-icon icon="mdi:history"></ha-icon>
          </button>
        </div>
        <div class="card-content">
          ${loading ? `
            <div class="loading-container">
              <div class="spinner"></div>
            </div>
          ` : meters.length === 0 ? `
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
              ${meters.map(meter => `
                <div class="meter-chip ${selectedMeter === meter.entity_id ? 'selected' : ''}"
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

  /**
   * Get the CSS styles specific to the meter selection component
   * @returns {string} CSS styles
   */
  static getStyles() {
    return `
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

      .refresh-btn {
        padding: 8px;
        background: transparent;
        border: none;
        border-radius: 50%;
        cursor: pointer;
        color: var(--secondary-text-color, #757575);
        transition: all 0.2s ease;
        margin-left: 8px;
      }

      .refresh-btn:hover {
        background: var(--divider-color, #e0e0e0);
      }
    `;
  }
}

// Export for module usage
window.MeterSelection = MeterSelection;
