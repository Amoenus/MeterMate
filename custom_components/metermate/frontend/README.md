# MeterMate Frontend - Home Assistant UI Integration

This directory contains the frontend implementation for MeterMate using Home Assistant's design system and UI components.

## Architecture

### Files Overview

- **`index.html`** - Main HTML entry point with HA theming
- **`src/`** - Source code directory organized by type
  - **`components/`** - UI Components
    - `metermate-panel.js` - Panel loader and element registration
    - `ha-metermate-panel.js` - Modern HA UI implementation
    - `meter-selection.js` - Meter selection component (extracted from main panel)
    - `ui-components.js` - Reusable UI components (legacy fallback)
  - **`services/`** - API and backend communication
    - `api.js` - API client for backend communication
  - **`utils/`** - Utility functions and polyfills
    - `ha-icon-polyfill.js` - Fallback for HA icons when not available
  - **`styles/`** - CSS styles
    - `main.css` - Main stylesheet with HA theming
- **`assets/`** - Static assets (if any)

### Modern Frontend Architecture

The new structure follows modern frontend best practices:

#### 📁 **Component-Based Architecture**
- Separated UI components from business logic
- Reusable components for consistent design
- Clear separation of concerns

#### 📁 **Service Layer**
- API client isolated in services directory
- Easy to test and mock
- Clean separation between data and presentation

#### 📁 **Utility Functions**
- Common utilities and polyfills
- Icon polyfill for HA compatibility
- Reusable helper functions

#### 📁 **Organized Styles**
- Single main stylesheet
- CSS custom properties for theming
- Responsive design patterns

### Home Assistant Design System Integration

The new implementation leverages Home Assistant's design language:

#### CSS Variables Used
- `--primary-background-color` - Main background
- `--primary-text-color` - Primary text color
- `--secondary-text-color` - Secondary text color
- `--card-background-color` - Card backgrounds
- `--primary-color` - Primary accent color
- `--divider-color` - Divider lines
- `--ha-card-box-shadow` - Card shadows
- `--ha-card-border-radius` - Card border radius
- `--paper-font-body1_-_font-family` - Typography

#### UI Components
- **Cards** - Using HA card styling with proper shadows and borders
- **Chips** - For meter selection with HA chip design patterns
- **Buttons** - Following HA button conventions
- **Dialogs** - Modal dialogs with HA styling
- **Tables** - Data tables with HA styling
- **FAB** - Floating Action Button for primary actions
- **Alerts** - Toast notifications with HA alert styling

#### Icons
- Uses `ha-icon` components with Material Design Icons
- Fallback polyfill for basic icon rendering
- Common icons: `mdi:meter-electric`, `mdi:plus`, `mdi:pencil`, `mdi:delete`

## Features

### Modern UI Elements
1. **Responsive Design** - Adapts to narrow/wide layouts
2. **Card-based Layout** - Following HA design patterns
3. **Interactive Elements** - Hover effects and transitions
4. **Accessibility** - Proper focus management and ARIA labels
5. **Theming** - Full integration with HA themes

### Functionality
1. **Meter Selection** - Chip-based meter selection
2. **Readings Management** - Add, edit, delete readings
3. **Data Visualization** - Sortable table with readings
4. **Real-time Updates** - Live data loading and updates
5. **Error Handling** - User-friendly error messages

## Integration Benefits

### Why Use HA UI Components?

1. **Consistency** - Matches Home Assistant's look and feel
2. **Theming** - Automatically adapts to user themes
3. **Accessibility** - Built-in accessibility features
4. **Responsiveness** - Mobile-friendly by default
5. **Maintenance** - Less custom CSS to maintain
6. **Future-proof** - Updates with Home Assistant

### User Experience Improvements

1. **Familiar Interface** - Users already know how to use it
2. **Theme Integration** - Works with dark/light modes
3. **Mobile Optimized** - Touch-friendly interactions
4. **Performance** - Efficient rendering and updates
5. **Keyboard Navigation** - Full keyboard support

## Technical Implementation

### Component Structure
```javascript
class HAMeterMatePanel extends HTMLElement {
  // HA-compatible property setters
  set hass(value) { /* Handle HA instance */ }
  set narrow(value) { /* Handle responsive layout */ }

  // State management
  _meters = []
  _readings = []
  _selectedMeter = null

  // Lifecycle methods
  connectedCallback() { /* Initialize */ }
  _render() { /* Update DOM */ }
}
```

### Styling Approach
```css
:host {
  /* Use HA CSS variables */
  background: var(--primary-background-color);
  color: var(--primary-text-color);
  font-family: var(--paper-font-body1_-_font-family);
}

.card {
  background: var(--card-background-color);
  border-radius: var(--ha-card-border-radius);
  box-shadow: var(--ha-card-box-shadow);
}
```

### Event Handling
- Uses standard DOM events
- Proper form validation
- Loading states and error handling
- Confirmation dialogs for destructive actions

## Development

### Adding New Features
1. Follow HA design patterns
2. Use HA CSS variables for theming
3. Implement proper loading/error states
4. Add responsive behavior
5. Test with different themes

### Best Practices
1. Use semantic HTML elements
2. Implement proper ARIA labels
3. Follow HA naming conventions
4. Test keyboard navigation
5. Ensure mobile compatibility

## Future Enhancements

### Potential Improvements
1. **Charts** - Add data visualization charts
2. **Filters** - Advanced filtering and search
3. **Export** - Data export functionality
4. **Bulk Operations** - Multi-select actions
5. **Real-time** - WebSocket updates
6. **Animations** - Smooth transitions and micro-interactions

### Advanced HA Integration
1. **Lovelace Cards** - Custom card components
2. **Dashboard Integration** - Embedded widgets
3. **Entity Cards** - Mini meter cards
4. **Automation** - Integration with HA automations
5. **Notifications** - HA notification system

## Component Architecture

The frontend is now structured with modular components for better maintainability:

#### MeterSelection Component (`meter-selection.js`)
- **Purpose**: Handles meter selection UI and interactions
- **Features**:
  - Chip-based meter display
  - Loading states and empty state handling
  - Refresh and rebuild history actions
  - Responsive design
- **API**: Static methods for rendering and styling
- **Usage**: Imported and used by the main panel component

#### Benefits of Modular Structure
- **Maintainability**: Each component has a single responsibility
- **Reusability**: Components can be used in different contexts
- **Testing**: Individual components can be tested in isolation
- **Performance**: Components can be loaded independently
- **Code Organization**: Clear separation of concerns

This implementation provides a solid foundation for a native-feeling Home Assistant integration while maintaining the flexibility to add advanced features in the future.
