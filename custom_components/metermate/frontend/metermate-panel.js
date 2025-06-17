// MeterMate Custom Panel for Home Assistant
// Main entry point following panel_custom pattern

(function() {
  'use strict';

  // Import modules from the integration's frontend path
  const script1 = document.createElement('script');
  script1.src = '/metermate/api.js';
  document.head.appendChild(script1);

  const script2 = document.createElement('script');
  script2.src = '/metermate/ui-components.js';
  document.head.appendChild(script2);

  const script3 = document.createElement('script');
  script3.src = '/metermate/meter-panel.js';
  document.head.appendChild(script3);

  const styles = document.createElement('link');
  styles.rel = 'stylesheet';
  styles.href = '/metermate/styles.css';
  document.head.appendChild(styles);

})();
