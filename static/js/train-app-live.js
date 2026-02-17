// Enhanced Train App with Live Data, Smart Suggestions, and Passenger Community Features (Waze-like)
function trainAppLive() {
    return {
        // Data properties
        stations: [],
        selectedStation: '',
        selectedStationName: '',
        viewType: 'departures',
        trainNumber: '',
        stationQuery: '',
        timetableData: [],
        trainData: null,
        trainSuggestions: [],
        stationSuggestions: [],
        
        // Passenger community data
        passengerReports: [],
        seatData: [],
        
        // UI state
        loading: false,
        loadingMessage: 'Loading...',
        error: '',
        errorSuggestions: [],
        showTrainSuggestions: false,
        showStationSuggestions: false,
        currentTime: '',
        lastUpdate: '',
        lastAction: null,
        
        // Passenger interaction modals
        showReportModal: false,
        showSeatModal: false,
        showTipModal: false,
        showQuickReportMenu: false,
        
        // Report form data
        reportType: 'delay',
        reportMessage: '',
        reportDelayMinutes: 0,
        reportPlatform: '',
        reportCrowding: 'comfortable',
        reportStation: '',
        reportSubmitting: false,
        
        // Seat report form data
        seatCarNumber: '',
        seatAvailable: 0,
        seatTotal: 0,
        seatStation: '',
        seatSubmitting: false,
        
        // Tip form data
        tipType: 'general',
        tipMessage: '',
        tipStation: '',
        tipSubmitting: false,
        
        // Connection and refresh
        connectionStatus: 'checking',
        connectionMessage: 'Checking connection...',
        showConnectionStatus: true,
        autoRefresh: false,
        refreshInterval: null,
        
        // CFR integration status
        cfrStatus: {
            accessible: false,
            lastChecked: null,
            trainPagesWork: false,
            stationsWork: false
        },
        dataSource: {
            type: 'unknown',
            cfrAttempted: false,
            cfrSuccessful: false,
            lastUpdate: null
        },

        // Dark mode
        darkMode: false,

        // Debounce timers
        suggestionTimer: null,
        stationSearchTimer: null,

        init() {
            this.loadStations();
            this.updateTime();
            this.checkConnection();
            this.checkCFRStatus();
            this.initDarkMode();
            
            // Update time every second
            setInterval(() => this.updateTime(), 1000);
            
            // Check connection every 30 seconds
            setInterval(() => this.checkConnection(), 30000);
            
            // Check CFR status every 5 minutes
            setInterval(() => this.checkCFRStatus(), 300000);
            
            // Close modals when clicking outside
            document.addEventListener('click', (e) => {
                if (e.target.classList.contains('modal-backdrop')) {
                    this.closeAllModals();
                }
            });
        },

        async checkCFRStatus() {
            try {
                const response = await fetch('/api/cfr-status');
                if (response.ok) {
                    this.cfrStatus = await response.json();
                    this.cfrStatus.lastChecked = new Date();
                }
            } catch (error) {
                console.error('Failed to check CFR status:', error);
                this.cfrStatus.accessible = false;
                this.cfrStatus.lastChecked = new Date();
            }
        },

        // Passenger Community Methods
        async loadTrainData() {
            if (!this.trainNumber.trim()) {
                this.error = 'Please enter a train number';
                return;
            }

            this.loading = true;
            this.loadingMessage = `Searching for train ${this.trainNumber}...`;
            this.error = '';
            this.lastAction = 'loadTrainData';

            // Clear station data when loading train data
            this.timetableData = [];
            this.selectedStation = '';
            this.selectedStationName = '';
            this.stationQuery = '';

            try {
                const response = await fetch(`/api/train/${encodeURIComponent(this.trainNumber)}`);
                
                if (response.ok) {
                    this.trainData = await response.json();
                    this.lastUpdate = this.formatTime(new Date());
                    
                    // Capture data source information
                    if (this.trainData.data_source) {
                        this.dataSource = this.trainData.data_source;
                        this.updateConnectionStatus();
                    }
                    
                    // Load passenger reports for this train
                    await this.loadPassengerReports(this.trainNumber);
                    await this.loadSeatData(this.trainNumber);
                    
                } else {
                    const errorData = await response.json();
                    this.error = errorData.message || 'Train not found';
                    this.errorSuggestions = errorData.suggestions || [];
                }
            } catch (error) {
                console.error('Failed to load train data:', error);
                this.error = 'Network error - please check your connection';
            } finally {
                this.loading = false;
            }
        },

        updateConnectionStatus() {
            if (this.dataSource.type === 'real_cfr_data') {
                this.connectionStatus = 'online';
                this.connectionMessage = 'Live CFR Data';
            } else if (this.dataSource.type === 'enhanced_demo_data') {
                if (this.dataSource.cfr_attempted) {
                    this.connectionStatus = 'fallback';
                    this.connectionMessage = 'Demo Mode (CFR attempted)';
                } else {
                    this.connectionStatus = 'fallback';
                    this.connectionMessage = 'Demo Mode';
                }
            } else {
                this.connectionStatus = 'checking';
                this.connectionMessage = 'Checking data source...';
            }
        },

        async loadPassengerReports(trainNumber) {
            try {
                const response = await fetch(`/api/passenger/reports/${encodeURIComponent(trainNumber)}`);
                if (response.ok) {
                    const data = await response.json();
                    this.passengerReports = data.reports || [];
                }
            } catch (error) {
                console.error('Failed to load passenger reports:', error);
            }
        },

        async loadSeatData(trainNumber) {
            try {
                const response = await fetch(`/api/passenger/seats/${encodeURIComponent(trainNumber)}`);
                if (response.ok) {
                    const data = await response.json();
                    this.seatData = data.seat_availability || [];
                }
            } catch (error) {
                console.error('Failed to load seat data:', error);
            }
        },

        async submitReport() {
            if (!this.trainData || !this.trainData.train_number) {
                alert('Please select a train first');
                return;
            }

            this.reportSubmitting = true;

            try {
                const reportData = {
                    train_number: this.trainData.train_number,
                    report_type: this.reportType,
                    message: this.reportMessage,
                    station_name: this.reportStation
                };

                if (this.reportType === 'delay') {
                    reportData.delay_minutes = this.reportDelayMinutes;
                } else if (this.reportType === 'platform') {
                    reportData.platform = this.reportPlatform;
                } else if (this.reportType === 'crowding') {
                    reportData.crowding_level = this.reportCrowding;
                }

                const response = await fetch('/api/passenger/report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(reportData)
                });

                if (response.ok) {
                    const result = await response.json();
                    this.showSuccessMessage(result.message);
                    this.closeAllModals();
                    this.clearReportForm();
                    
                    // Reload reports to show the new one
                    await this.loadPassengerReports(this.trainData.train_number);
                } else {
                    const error = await response.json();
                    alert(error.error || 'Failed to submit report');
                }
            } catch (error) {
                console.error('Failed to submit report:', error);
                alert('Network error - please try again');
            } finally {
                this.reportSubmitting = false;
            }
        },

        async submitSeatReport() {
            if (!this.trainData || !this.trainData.train_number) {
                alert('Please select a train first');
                return;
            }

            this.seatSubmitting = true;

            try {
                const seatData = {
                    train_number: this.trainData.train_number,
                    car_number: this.seatCarNumber,
                    available_seats: parseInt(this.seatAvailable),
                    total_seats: parseInt(this.seatTotal),
                    station_name: this.seatStation
                };

                const response = await fetch('/api/passenger/seats', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(seatData)
                });

                if (response.ok) {
                    const result = await response.json();
                    this.showSuccessMessage(result.message);
                    this.closeAllModals();
                    this.clearSeatForm();
                    
                    // Reload seat data
                    await this.loadSeatData(this.trainData.train_number);
                } else {
                    const error = await response.json();
                    alert(error.error || 'Failed to submit seat info');
                }
            } catch (error) {
                console.error('Failed to submit seat info:', error);
                alert('Network error - please try again');
            } finally {
                this.seatSubmitting = false;
            }
        },

        async submitTip() {
            this.tipSubmitting = true;

            try {
                const tipData = {
                    tip_type: this.tipType,
                    message: this.tipMessage,
                    station_name: this.tipStation
                };

                const response = await fetch('/api/passenger/tips', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(tipData)
                });

                if (response.ok) {
                    const result = await response.json();
                    this.showSuccessMessage(result.message);
                    this.closeAllModals();
                    this.clearTipForm();
                } else {
                    const error = await response.json();
                    alert(error.error || 'Failed to submit tip');
                }
            } catch (error) {
                console.error('Failed to submit tip:', error);
                alert('Network error - please try again');
            } finally {
                this.tipSubmitting = false;
            }
        },

        async verifyReport(report) {
            // In a real implementation, you'd need report IDs
            console.log('Verifying report:', report);
            // This would call /api/passenger/verify/{report_id}
        },

        closeAllModals() {
            this.showReportModal = false;
            this.showSeatModal = false;
            this.showTipModal = false;
            this.showQuickReportMenu = false;
        },

        clearReportForm() {
            this.reportType = 'delay';
            this.reportMessage = '';
            this.reportDelayMinutes = 0;
            this.reportPlatform = '';
            this.reportCrowding = 'comfortable';
            this.reportStation = '';
        },

        clearSeatForm() {
            this.seatCarNumber = '';
            this.seatAvailable = 0;
            this.seatTotal = 0;
            this.seatStation = '';
        },

        clearTipForm() {
            this.tipType = 'general';
            this.tipMessage = '';
            this.tipStation = '';
        },

        getReportIcon(reportType) {
            const icons = {
                delay: 'fas fa-clock text-red-500',
                platform: 'fas fa-exchange-alt text-yellow-500',
                crowding: 'fas fa-users text-purple-500',
                info: 'fas fa-info-circle text-blue-500'
            };
            return icons[reportType] || 'fas fa-comment text-gray-500';
        },

        getReportTitle(reportType) {
            const titles = {
                delay: 'Delay Report',
                platform: 'Platform Change',
                crowding: 'Crowding Level',
                info: 'Information'
            };
            return titles[reportType] || 'Report';
        },

        showSuccessMessage(message) {
            // Simple success indication - could be enhanced with a toast system
            console.log('Success:', message);
            
            // Temporary visual feedback
            const originalStatus = this.connectionMessage;
            this.connectionMessage = message;
            this.connectionStatus = 'online';
            
            setTimeout(() => {
                this.connectionMessage = originalStatus;
            }, 3000);
        },

        // Original methods (simplified versions)
        async loadStations() {
            try {
                const response = await fetch('/get-stations/');
                if (response.ok) {
                    const data = await response.json();
                    this.stations = data.stations || data;
                    this.connectionStatus = 'online';
                    this.connectionMessage = 'Connected to CFR API';
                } else {
                    this.connectionStatus = 'fallback';
                    this.connectionMessage = 'Using fallback data';
                }
            } catch (error) {
                this.connectionStatus = 'offline';
                this.connectionMessage = 'Connection failed';
                console.error('Failed to load stations:', error);
            }
        },

        async getTrainSuggestions() {
            if (!this.trainNumber || this.trainNumber.length < 2) {
                this.trainSuggestions = [];
                return;
            }

            clearTimeout(this.suggestionTimer);
            this.suggestionTimer = setTimeout(async () => {
                try {
                    const response = await fetch(`/api/train-suggestions/${encodeURIComponent(this.trainNumber)}`);
                    if (response.ok) {
                        this.trainSuggestions = await response.json();
                    }
                } catch (error) {
                    console.error('Failed to get train suggestions:', error);
                }
            }, 300);
        },

        selectTrainSuggestion(suggestion) {
            this.trainNumber = suggestion.train_number;
            this.showTrainSuggestions = false;
            this.trainSuggestions = [];
            
            // Automatically load train data when suggestion is selected
            this.loadTrainData();
        },

        // Method to clear all search results and start fresh
        clearAllResults() {
            // Clear train data
            this.trainData = null;
            this.trainNumber = '';
            this.passengerReports = [];
            this.seatData = [];
            
            // Clear station data
            this.timetableData = [];
            this.selectedStation = '';
            this.selectedStationName = '';
            this.stationQuery = '';
            
            // Clear suggestions
            this.trainSuggestions = [];
            this.stationSuggestions = [];
            this.showTrainSuggestions = false;
            this.showStationSuggestions = false;
            
            // Clear error states
            this.error = '';
            this.errorSuggestions = [];
            this.loading = false;
            
            console.log('All search results cleared');
        },

        async searchStations() {
            if (!this.stationQuery || this.stationQuery.length < 2) {
                this.stationSuggestions = [];
                return;
            }

            clearTimeout(this.stationSearchTimer);
            this.stationSearchTimer = setTimeout(async () => {
                try {
                    const query = encodeURIComponent(this.stationQuery);
                    const response = await fetch(`/api/stations/search/${query}`);
                    if (response.ok) {
                        this.stationSuggestions = await response.json();
                    }
                } catch (error) {
                    console.error('Failed to search stations:', error);
                }
            }, 300);
        },

        selectStation(station) {
            this.selectedStation = station.station_id;
            this.selectedStationName = station.name;
            this.stationQuery = station.name;
            this.showStationSuggestions = false;
            this.stationSuggestions = [];
            
            // Automatically load station data when station is selected
            this.loadStationData();
        },

        async loadStationData() {
            if (!this.selectedStation) return;

            this.loading = true;
            this.error = '';
            this.lastAction = 'loadStationData';
            
            // Clear train data when loading station data
            this.trainData = null;
            this.trainNumber = '';
            this.passengerReports = [];
            this.seatData = [];
            
            try {
                const endpoint = `/station/${this.selectedStation}/${this.viewType}/current`;
                const response = await fetch(endpoint);
                
                if (response.ok) {
                    this.timetableData = await response.json();
                    this.lastUpdate = this.formatTime(new Date());
                } else {
                    this.error = 'Failed to load station data';
                }
            } catch (error) {
                this.error = 'Network error';
                console.error('Failed to load station data:', error);
            } finally {
                this.loading = false;
            }
        },

        updateTime() {
            const now = new Date();
            this.currentTime = this.formatTime(now);
        },

        formatTime(date) {
            if (!date) return 'N/A';
            
            try {
                const parsedDate = typeof date === 'string' ? new Date(date) : date;
                return parsedDate.toLocaleTimeString('ro-RO', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (error) {
                return 'Invalid time';
            }
        },

        getDelayBadgeClass(delay) {
            if (!delay || delay === 0) return 'bg-green-500';
            if (delay <= 5) return 'bg-yellow-500';
            if (delay <= 15) return 'bg-orange-500';
            return 'bg-red-500';
        },

        getStationTypeClass(stop) {
            if (stop.is_origin) return 'bg-green-500 w-4 h-4 rounded-full mr-3';
            if (stop.is_destination) return 'bg-red-500 w-4 h-4 rounded-full mr-3';
            return 'bg-blue-500 w-3 h-3 rounded-full mr-3 mt-1';
        },

        async checkConnection() {
            try {
                const response = await fetch('/api');
                if (response.ok) {
                    this.connectionStatus = 'online';
                    this.connectionMessage = 'Connected';
                } else {
                    this.connectionStatus = 'fallback';
                    this.connectionMessage = 'Limited connectivity';
                }
            } catch (error) {
                this.connectionStatus = 'offline';
                this.connectionMessage = 'Offline';
            }
        },

        retryLastAction() {
            if (this.lastAction && typeof this[this.lastAction] === 'function') {
                this[this.lastAction]();
            }
        },

        toggleAutoRefresh() {
            this.autoRefresh = !this.autoRefresh;
            
            if (this.autoRefresh) {
                this.refreshInterval = setInterval(() => {
                    if (this.selectedStation) {
                        this.loadStationData();
                    }
                    if (this.trainData) {
                        this.loadTrainData();
                    }
                }, 30000); // Refresh every 30 seconds
            } else {
                clearInterval(this.refreshInterval);
                this.refreshInterval = null;
            }
        },

        initDarkMode() {
            // Check localStorage for saved preference
            const saved = localStorage.getItem('darkMode');
            if (saved !== null) {
                this.darkMode = JSON.parse(saved);
            } else {
                // Check system preference
                this.darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
            }
            
            this.applyDarkMode();
            
            // Listen for system theme changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (localStorage.getItem('darkMode') === null) {
                    this.darkMode = e.matches;
                    this.applyDarkMode();
                }
            });
        },

        toggleDarkMode() {
            this.darkMode = !this.darkMode;
            localStorage.setItem('darkMode', JSON.stringify(this.darkMode));
            this.applyDarkMode();
        },

        applyDarkMode() {
            if (this.darkMode) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
        },

        // Train composition helper methods
        getClassBadgeColor(carClass) {
            switch(carClass) {
                case '1st':
                    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
                case '2nd':
                    return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
                case 'Restaurant':
                    return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
                case 'Bistro':
                    return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300';
                case '1st/2nd':
                    return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300';
                default:
                    return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300';
            }
        },

        // Visual car representation for train formation display
        getCarVisualClass(carClass, carType) {
            // Determine visual class based on car type and class
            if (carType && carType.toLowerCase().includes('restaurant') || carType === 'WRmee') {
                return 'car-restaurant';
            }
            if (carType && (carType.toLowerCase().includes('bistro') || carType === 'ARee')) {
                return 'car-bistro';
            }
            if (carType && (carType.toLowerCase().includes('sleeper') || carType === 'WL' || carType === 'WLmee')) {
                return 'car-sleeper';
            }
            if (carType && (carType.toLowerCase().includes('couchette') || carType === 'Bcmee')) {
                return 'car-couchette';
            }
            
            // Default to class-based coloring
            switch(carClass) {
                case '1st':
                    return 'car-first-class';
                case '2nd':
                    return 'car-second-class';
                case 'Restaurant':
                    return 'car-restaurant';
                case 'Bistro':
                    return 'car-bistro';
                case '1st/2nd':
                    return 'car-sleeper';
                default:
                    return 'car-default';
            }
        },

        // SVG car color functions for VagonWeb-style rendering
        getCarColor(carClass, carType) {
            // Restaurant cars
            if (carType && (carType.includes('WR') || carClass === 'Restaurant')) {
                return '#dc2626'; // Red
            }
            // Bistro cars  
            if (carType && (carType.includes('AR') || carClass === 'Bistro')) {
                return '#ea580c'; // Orange
            }
            // Sleeping cars
            if (carType && (carType.includes('WL') || carClass.includes('1st/2nd'))) {
                return '#7c3aed'; // Purple
            }
            // Couchette cars
            if (carType && carType.includes('Bcmee')) {
                return '#8b5cf6'; // Light purple
            }
            
            // Class-based colors
            switch(carClass) {
                case '1st':
                    return '#dc2626'; // Red for first class
                case '2nd':
                    return '#2563eb'; // Blue for second class
                default:
                    return '#6b7280'; // Gray default
            }
        },

        getCarStrokeColor(carClass, carType) {
            // Darker stroke version of main color
            if (carType && (carType.includes('WR') || carClass === 'Restaurant')) {
                return '#b91c1c';
            }
            if (carType && (carType.includes('AR') || carClass === 'Bistro')) {
                return '#c2410c';
            }
            if (carType && (carType.includes('WL') || carClass.includes('1st/2nd'))) {
                return '#6d28d9';
            }
            if (carType && carType.includes('Bcmee')) {
                return '#7c3aed';
            }
            
            switch(carClass) {
                case '1st':
                    return '#b91c1c';
                case '2nd':
                    return '#1d4ed8';
                default:
                    return '#4b5563';
            }
        },

        getCarRoofColor(carClass, carType) {
            // Slightly lighter roof color
            if (carType && (carType.includes('WR') || carClass === 'Restaurant')) {
                return '#ef4444';
            }
            if (carType && (carType.includes('AR') || carClass === 'Bistro')) {
                return '#f97316';
            }
            if (carType && (carType.includes('WL') || carClass.includes('1st/2nd'))) {
                return '#8b5cf6';
            }
            if (carType && carType.includes('Bcmee')) {
                return '#a855f7';
            }
            
            switch(carClass) {
                case '1st':
                    return '#ef4444';
                case '2nd':
                    return '#3b82f6';
                default:
                    return '#9ca3af';
            }
        },

        getWindowCount(carType) {
            // Different car types have different window configurations
            if (carType && (carType.includes('WR') || carType.includes('AR'))) {
                return 4; // Restaurant/Bistro cars have fewer, larger windows
            }
            if (carType && carType.includes('WL')) {
                return 3; // Sleeping cars have fewer windows
            }
            if (carType && carType.includes('Bcmee')) {
                return 5; // Couchette cars
            }
            return 6; // Standard passenger cars
        }
    };
}
