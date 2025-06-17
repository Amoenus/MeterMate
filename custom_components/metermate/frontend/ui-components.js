// MeterMate UI Components
// Reusable UI components and utilities

window.MeterMateUI = (function() {
  'use strict';

  class UIComponents {
    // Create a button
    static createButton(text, className, onClick) {
      const button = document.createElement('button');
      button.textContent = text;
      button.className = `btn ${className}`;
      if (onClick) {
        button.addEventListener('click', onClick);
      }
      return button;
    }

    // Create a form input
    static createInput(type, name, placeholder, required = false) {
      const input = document.createElement('input');
      input.type = type;
      input.name = name;
      input.placeholder = placeholder;
      input.required = required;
      return input;
    }

    // Create a select dropdown
    static createSelect(name, options) {
      const select = document.createElement('select');
      select.name = name;

      options.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option.value;
        optionElement.textContent = option.text;
        optionElement.selected = option.selected || false;
        select.appendChild(optionElement);
      });

      return select;
    }

    // Create a modal overlay
    static createModal(title, content) {
      const overlay = document.createElement('div');
      overlay.className = 'form-overlay';

      const container = document.createElement('div');
      container.className = 'form-container';

      const header = document.createElement('h2');
      header.textContent = title;
      container.appendChild(header);

      container.appendChild(content);
      overlay.appendChild(container);

      return overlay;
    }

    // Create a stats card
    static createStatCard(title, value) {
      const card = document.createElement('div');
      card.className = 'stat-card';

      const h3 = document.createElement('h3');
      h3.textContent = title;

      const valueDiv = document.createElement('div');
      valueDiv.className = 'value';
      valueDiv.textContent = value;

      card.appendChild(h3);
      card.appendChild(valueDiv);

      return card;
    }

    // Create a readings table row
    static createReadingRow(reading, onEdit, onDelete) {
      const row = document.createElement('div');
      row.className = 'reading-row';

      const timestamp = document.createElement('div');
      timestamp.textContent = new Date(reading.timestamp).toLocaleString();

      const value = document.createElement('div');
      value.textContent = `${reading.value.toFixed(2)} ${reading.unit || 'kWh'}`;

      const type = document.createElement('div');
      type.textContent = reading.reading_type || 'cumulative';

      const notes = document.createElement('div');
      notes.textContent = reading.notes || '—';

      const actions = document.createElement('div');
      actions.className = 'reading-actions';

      const editBtn = UIComponents.createButton('✏️ Edit', 'btn-small btn-edit', () => onEdit(reading));
      const deleteBtn = UIComponents.createButton('🗑️ Delete', 'btn-small btn-delete', () => onDelete(reading));

      actions.appendChild(editBtn);
      actions.appendChild(deleteBtn);

      row.appendChild(timestamp);
      row.appendChild(value);
      row.appendChild(type);
      row.appendChild(notes);
      row.appendChild(actions);

      return row;
    }

    // Utility: Format datetime for input
    static formatDateTimeForInput(timestamp) {
      if (!timestamp) return '';
      return new Date(timestamp).toISOString().slice(0, 16);
    }

    // Utility: Show loading state
    static showLoading(container, message = 'Loading...') {
      container.innerHTML = `<div class="loading">⏳ ${message}</div>`;
    }

    // Utility: Show empty state
    static showEmptyState(container, title, message) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>${title}</h3>
          <p>${message}</p>
        </div>
      `;
    }

    // Utility: Show error
    static showError(message) {
      alert(`Error: ${message}`);
    }

    // Utility: Confirm action
    static confirm(message) {
      return confirm(message);
    }

    // Create a header
    static createHeader(title) {
      const header = document.createElement('div');
      header.className = 'panel-header';

      const h1 = document.createElement('h1');
      h1.textContent = title;
      header.appendChild(h1);

      return header;
    }

    // Create a loader
    static createLoader() {
      const loader = document.createElement('div');
      loader.className = 'loader';
      loader.innerHTML = '<div class="spinner"></div><p>Loading...</p>';
      return loader;
    }

    // Create a form group (label + input)
    static createFormGroup(labelText, input) {
      const group = document.createElement('div');
      group.className = 'form-group';

      const label = document.createElement('label');
      label.textContent = labelText;
      group.appendChild(label);
      group.appendChild(input);

      return group;
    }

    // Create a table
    static createTable(headers, rows) {
      const table = document.createElement('table');
      table.className = 'readings-table';

      // Create header
      const thead = document.createElement('thead');
      const headerRow = document.createElement('tr');

      headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        headerRow.appendChild(th);
      });

      thead.appendChild(headerRow);
      table.appendChild(thead);

      // Create body
      const tbody = document.createElement('tbody');

      rows.forEach(rowData => {
        const tr = document.createElement('tr');

        rowData.forEach(cellData => {
          const td = document.createElement('td');
          if (typeof cellData === 'string') {
            td.textContent = cellData;
          } else {
            td.appendChild(cellData);
          }
          tr.appendChild(td);
        });

        tbody.appendChild(tr);
      });

      table.appendChild(tbody);
      return table;
    }
  }

  return {
    UIComponents
  };
})();
