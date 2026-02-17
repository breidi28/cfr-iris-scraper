# 🚂 CFR Train Tracker - Enhanced Live Version

A modern, feature-rich web application for tracking Romanian Railways (CFR) trains with **real-time data** and **intelligent search suggestions**.

## 🆕 **What's New in the Live Version**

### **🔍 Smart Search Suggestions**
- **Train Number Suggestions**: Type "IR" and get suggestions like "IR 1621", "IR 1622"
- **Station Name Autocomplete**: Search for stations with real-time filtering
- **Pattern Recognition**: Intelligent matching for Romanian train naming conventions
- **Common Routes**: Quick access to popular train routes

### **📡 Real-Time Data Integration**
- **Live API Connection**: Direct integration with CFR's official data source
- **Connection Status Indicator**: Visual feedback for online/offline status
- **Auto-refresh**: Automatic data updates every 30 seconds (toggleable)
- **Last Update Timestamps**: Know exactly when data was last refreshed

### **🛡️ Enhanced Error Handling**
- **Graceful Degradation**: App works even when APIs are temporarily down
- **Detailed Error Messages**: Clear explanations with actionable suggestions
- **Retry Mechanisms**: Smart retry logic with user feedback
- **Connection Recovery**: Automatic reconnection attempts

## 🎯 **Key Features for Passengers**

### **🚉 Station Information**
```
✅ Real-time departures and arrivals
✅ Current delays and platform changes
✅ Live connection status
✅ Auto-refreshing timetables
✅ Search by station name
```

### **🚂 Train Tracking**
```
✅ Complete journey details with all stops
✅ Real-time delay information
✅ Platform assignments
✅ Smart train number suggestions
✅ Route visualization
```

### **📱 Mobile Experience**
```
✅ Responsive design for all devices
✅ Touch-friendly interface
✅ Offline support with service worker
✅ Progressive Web App (PWA) features
✅ Install as phone app
```

### **🔔 Smart Notifications**
```
✅ Browser notifications for departures
✅ 5-minute advance warnings
✅ Train-specific alerts
✅ Platform change notifications
```

## 🌐 **Available Endpoints**

### **Live Data Endpoints**
- `GET /` → Live train tracker interface
- `GET /live` → Same as above (explicit route)
- `GET /get-stations/` → All available stations
- `GET /station/{id}/departures/current` → Live departures
- `GET /station/{id}/arrivals/current` → Live arrivals
- `GET /train/{number}` → Complete train journey
- `GET /api/train/{number}` → Enhanced train data with metadata

### **Smart Search Endpoints**
- `GET /api/train-suggestions/{query}` → Train number suggestions
- `GET /api/stations/search/{query}` → Station name search
- `GET /reload-stations/` → Manual station data refresh

### **Demo & Testing**
- `GET /demo` → Demo with sample data
- `GET /api/demo/*` → Demo endpoints for testing

## 🚀 **Getting Started**

### **Prerequisites**
```bash
# Install Python dependencies
pip install flask flask-cors requests-html viewstate python-dateutil
```

### **Quick Start**
```bash
# Clone or download the project
cd cfr-iris-scraper

# Start the application
python app.py

# Open in browser
# Live version: http://localhost:5000
# Demo version: http://localhost:5000/demo
```

### **Development Mode**
```bash
# Enable debug mode (automatic restart on changes)
export FLASK_ENV=development  # Linux/Mac
$env:FLASK_ENV="development"  # Windows PowerShell

python app.py
```

## 💡 **How to Use**

### **🔍 Finding Trains**
1. **By Station**: 
   - Type station name (e.g., "București", "Cluj")
   - Select from autocomplete suggestions
   - Choose departures or arrivals
   - Enable auto-refresh for live updates

2. **By Train Number**:
   - Start typing train number (e.g., "IR", "IC 5")
   - Select from intelligent suggestions
   - Get complete journey details

### **🎯 Pro Tips**
- **Enable Auto-refresh**: Toggle the auto-refresh button for live updates
- **Use Suggestions**: Don't memorize train numbers - use the smart suggestions
- **Check Connection**: Watch the connection indicator in the top-right
- **Set Notifications**: Click "Notify Me" for departure alerts
- **Install as App**: Use browser's "Add to Home Screen" for quick access

## 🛠️ **Technical Architecture**

### **Backend (Python Flask)**
```python
# Smart suggestion algorithm
@app.route('/api/train-suggestions/<query>')
def get_train_suggestions(query):
    # Pattern matching for Romanian train types
    # IR (InterRegio), IC (InterCity), R (Regio), etc.
    # Returns scored suggestions based on relevance
```

### **Frontend (Modern JavaScript)**
```javascript
// Real-time search with debouncing
async function getTrainSuggestions() {
    // 300ms debounce to avoid API spam
    // Intelligent caching for better performance
    // Visual feedback for all user interactions
}
```

### **Data Flow**
```
User Input → Debounced Search → API Call → Smart Suggestions → User Selection → Live Data
```

## 🎨 **UI/UX Features**

### **Visual Design**
- **Glassmorphism**: Modern translucent cards with backdrop blur
- **Color-Coded Status**: Intuitive colors for delays and departures
- **Responsive Layout**: Perfect on phones, tablets, and desktop
- **Dark Mode Support**: Automatic detection of user preference

### **Interaction Design**
- **Smooth Animations**: Card hover effects and smooth transitions
- **Loading States**: Visual feedback for all async operations
- **Error Recovery**: Clear error messages with retry options
- **Progressive Enhancement**: Works without JavaScript for basic features

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Optional: Custom port
export PORT=5000

# Optional: Debug mode
export FLASK_DEBUG=1

# Optional: Host binding
export FLASK_HOST=0.0.0.0
```

### **API Timeouts**
```python
# Connection timeout for external APIs (default: 30 seconds)
EXTERNAL_API_TIMEOUT = 30

# Auto-refresh interval (default: 30 seconds)
AUTO_REFRESH_INTERVAL = 30000  # milliseconds
```

## 📊 **Performance Features**

### **Caching Strategy**
- **Service Worker**: Caches static assets for offline use
- **Smart Debouncing**: Prevents API spam during typing
- **Connection Pooling**: Efficient HTTP connection reuse
- **Lazy Loading**: Load data only when needed

### **Error Recovery**
- **Circuit Breaker**: Temporary API failure handling
- **Exponential Backoff**: Smart retry timing
- **Graceful Degradation**: Partial functionality during outages
- **User Feedback**: Clear communication of system status

## 🚀 **Production Deployment**

### **Using Gunicorn (Recommended)**
```bash
# Install Gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### **Using Docker**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### **Nginx Reverse Proxy**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🤝 **Contributing**

### **Development Setup**
```bash
# Clone repository
git clone <repo-url>
cd cfr-iris-scraper

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python app.py
```

### **Feature Requests**
- Real-time push notifications
- Route planning with connections
- Historical delay analysis
- Multi-language support
- Ticket integration

## 📱 **Browser Support**

| Browser | Status | Notes |
|---------|--------|-------|
| Chrome/Edge | ✅ Full | Recommended browser |
| Firefox | ✅ Full | All features supported |
| Safari | ✅ Full | Including iOS Safari |
| Mobile Chrome | ✅ Full | Optimized for mobile |
| Mobile Safari | ✅ Full | iOS app-like experience |

## 🆘 **Troubleshooting**

### **Common Issues**
1. **"Stations not available"**
   - External API is down
   - Try the `/reload-stations/` endpoint
   - Use demo mode for testing

2. **Train not found**
   - Check train number format
   - Use suggestion system
   - Verify train runs today

3. **Connection issues**
   - Check internet connection
   - Look for connection status indicator
   - Try refreshing the page

### **Debug Mode**
```bash
# Enable verbose logging
export FLASK_DEBUG=1
python app.py

# Check browser console for client-side errors
# Open Developer Tools (F12) → Console
```

---

**Built with ❤️ for Romanian train passengers** 🇷🇴

*Real-time data, smart suggestions, modern design - everything you need for your train journey!*
