# CFR Train Tracker - Modern Passenger App

A modern, responsive web application for tracking Romanian Railways (CFR) trains with a beautiful user interface designed specifically for passengers.

## Features

### 🚂 **Passenger-Focused Design**
- **Real-time Departures & Arrivals**: View current timetables for any station
- **Train Journey Tracking**: Follow a specific train's entire route with live updates
- **Modern UI**: Beautiful, mobile-responsive interface with glassmorphism design
- **Delay Information**: Clear visual indicators for on-time, delayed, and cancelled trains
- **Platform Information**: See which platform your train will use

### 📱 **Mobile-First Experience**
- **Responsive Design**: Works perfectly on phones, tablets, and desktop
- **PWA Support**: Install as an app on your phone for offline access
- **Touch-Friendly**: Large buttons and touch targets for mobile use
- **Fast Loading**: Optimized for slow mobile connections

### 🔔 **Smart Notifications**
- **Departure Alerts**: Get notified 5 minutes before your train departs
- **Real-time Updates**: Automatic refresh every 30 seconds when viewing timetables
- **Browser Notifications**: Native browser notification support

### 🎨 **Modern Interface**
- **Glassmorphism Design**: Beautiful translucent cards with backdrop blur
- **Color-Coded Status**: Intuitive color system for train status
- **Icons & Typography**: Clean, readable design with Font Awesome icons
- **Dark Mode Support**: Automatic dark mode detection

## Demo Version

Visit `/demo` to see the application with sample data:
- **Sample Stations**: Major Romanian cities (București, Cluj, Brașov, etc.)
- **Realistic Data**: Simulated train schedules with delays and platforms
- **Full Functionality**: All features work with demo data

Try these in demo mode:
1. Select "București Nord" and view departures
2. Search for train "IR 1621" to see journey details
3. Test the notification system (shows demo alert)

## Technical Features

### 🛡️ **Robust Error Handling**
- **Graceful Degradation**: App works even when external APIs are down
- **User-Friendly Errors**: Clear error messages instead of technical details
- **Retry Mechanisms**: Manual retry option for failed station loading
- **Offline Support**: Service worker for offline functionality

### ⚡ **Performance Optimized**
- **Fast Loading**: Minimal external dependencies
- **Efficient Updates**: Only refresh data when needed
- **Caching**: Service worker caches static assets
- **Progressive Enhancement**: Works without JavaScript for basic functionality

### 🔧 **Developer-Friendly**
- **Clean Code**: Well-structured HTML, CSS, and JavaScript
- **Accessibility**: ARIA labels, keyboard navigation, screen reader support
- **Cross-Browser**: Works on all modern browsers
- **Documentation**: Comprehensive inline documentation

## API Endpoints

### Production Endpoints
- `GET /` - Main application interface
- `GET /get-stations/` - List all available stations
- `GET /reload-stations/` - Manually reload station data
- `GET /station/{id}/departures/current` - Current departures for a station
- `GET /station/{id}/arrivals/current` - Current arrivals for a station
- `GET /train/{number}` - Full journey details for a specific train

### Demo Endpoints
- `GET /demo` - Demo version with sample data
- `GET /api/demo/stations` - Sample stations
- `GET /api/demo/station/{id}/departures/current` - Sample departures
- `GET /api/demo/train/{number}` - Sample train journey

## Installation & Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Access the Application**:
   - Production: `http://localhost:5000`
   - Demo: `http://localhost:5000/demo`

## Passenger Use Cases

### 🚶 **At the Station**
- Quick departure board view
- Platform information
- Real-time delay updates
- Next few hours of departures

### 🏠 **Planning Your Trip**
- Check departure times before leaving home
- Set notifications for your train
- View full journey with all stops
- Check for delays before traveling

### 🚂 **On the Train**
- Track your journey progress
- See upcoming stops
- Check arrival times
- Platform information for connections

### 📱 **Mobile Experience**
- Works offline once loaded
- Fast, touch-friendly interface
- Notification support
- Install as phone app

## Design Philosophy

This application is designed specifically for **passengers**, not just train enthusiasts or developers. Every feature focuses on what people actually need when traveling:

- **Clarity over Complexity**: Simple, clear information display
- **Speed over Features**: Fast loading and quick access to essential info
- **Mobile-First**: Most passengers check trains on their phone
- **Real-World Usage**: Designed for actual train stations and travel scenarios

## Technology Stack

- **Backend**: Python Flask with error handling and graceful degradation
- **Frontend**: Modern HTML5, CSS3, and vanilla JavaScript
- **UI Framework**: Tailwind CSS for responsive design
- **State Management**: Alpine.js for reactive components
- **Icons**: Font Awesome for consistent iconography
- **PWA Features**: Service worker for offline support and app installation

## Browser Support

- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari (including iOS)
- ✅ Mobile browsers
- ⚠️ Internet Explorer (basic functionality only)

---

**Built for Romanian Railway passengers** 🇷🇴 🚂
