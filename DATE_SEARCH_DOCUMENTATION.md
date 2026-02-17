# Date Search Functionality for Train Tracker

## Overview
The Train Tracker now supports date-based search functionality, allowing users to search for trains and view schedules for specific dates within the data validity period.

## Data Validity Period
- **Data Source**: Official CFR data from data.gov.ro
- **Valid From**: 2024-12-15
- **Valid Until**: 2025-12-13
- **Export Date**: 2024-12-09

## New API Endpoints

### 1. Data Validity Information
```
GET /api/data-validity
```

**Response:**
```json
{
  "valid_from": "2024-12-15",
  "valid_until": "2025-12-13", 
  "export_date": "2024-12-09",
  "is_current": true,
  "days_remaining": 131
}
```

### 2. Train Lookup with Date
```
GET /api/train/<train_id>?date=YYYY-MM-DD
GET /train/<train_id>?date=YYYY-MM-DD
```

**Examples:**
- `/api/train/IC 536?date=2025-06-15` - Get IC 536 schedule for June 15, 2025
- `/api/train/IR 1655` - Get IR 1655 schedule (current validity period)

**Valid Date Response:**
```json
{
  "train_number": "IC 536",
  "stations": [...],
  "summary": {
    "origin": "Constanţa",
    "destination": "Braşov",
    "total_stations": 12,
    "category": "IC",
    "operator": "CFR Călători"
  },
  "data_source": {
    "type": "government_official_data",
    "source": "data.gov.ro CFR Călători",
    "search_date": "2025-06-15",
    "data_validity": {
      "valid_from": "2024-12-15",
      "valid_until": "2025-12-13"
    }
  }
}
```

**Invalid Date Response (400 Bad Request):**
```json
{
  "error": "Date out of range",
  "message": "Date 2026-01-01 is outside data validity period",
  "valid_from": "2024-12-15",
  "valid_until": "2025-12-13"
}
```

### 3. Train Search with Date
```
GET /api/search/trains?q=<query>&date=YYYY-MM-DD
```

**Examples:**
- `/api/search/trains?q=IC&date=2025-06-15` - Search IC trains for June 15, 2025
- `/api/search/trains?q=536` - Search for train 536 (current validity period)

**Response:**
```json
{
  "query": "IC",
  "search_date": "2025-06-15",
  "results": [
    {
      "train_number": "IC 521a",
      "category": "IC",
      "relevance": "category",
      "search_date": "2025-06-15"
    }
  ],
  "count": 14,
  "data_source": {
    "type": "government_official_data",
    "source": "data.gov.ro CFR Călători"
  }
}
```

## Frontend Integration

### HTML Date Input
```html
<input type="date" 
       id="searchDate" 
       min="2024-12-15" 
       max="2025-12-13" 
       value="">
```

### JavaScript Integration
```javascript
// Get data validity information
async function getDataValidity() {
    const response = await fetch('/api/data-validity');
    return await response.json();
}

// Search trains with date
async function searchTrainsWithDate(query, date = null) {
    let url = `/api/search/trains?q=${encodeURIComponent(query)}`;
    if (date) {
        url += `&date=${date}`;
    }
    
    const response = await fetch(url);
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Search failed');
    }
    
    return await response.json();
}

// Get train data with date
async function getTrainWithDate(trainId, date = null) {
    let url = `/api/train/${encodeURIComponent(trainId)}`;
    if (date) {
        url += `?date=${date}`;
    }
    
    const response = await fetch(url);
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Train not found');
    }
    
    return await response.json();
}
```

### Error Handling
```javascript
try {
    const trainData = await getTrainWithDate('IC 536', '2026-01-01');
} catch (error) {
    if (error.message.includes('outside data validity period')) {
        // Show date picker with valid range
        showDateValidityError();
    }
}
```

## Usage Examples

### 1. Initialize and check data validity
```python
from government_integration import init_government_data, get_data_validity_info

# Initialize data
init_government_data()

# Check validity
validity = get_data_validity_info()
print(f"Data valid from {validity['valid_from']} to {validity['valid_until']}")
```

### 2. Search trains for specific date
```python
from government_integration import search_government_trains, is_date_valid

# Validate date first
if is_date_valid('2025-06-15'):
    results = search_government_trains('IC', '2025-06-15')
    print(f"Found {len(results)} IC trains for 2025-06-15")
```

### 3. Get train data for specific date
```python
from government_integration import get_government_train_data

# Get train with date
train_data = get_government_train_data('IC 536', '2025-06-15')
if train_data and 'error' not in train_data:
    print(f"IC 536 on 2025-06-15: {train_data['summary']['origin']} → {train_data['summary']['destination']}")
```

## Implementation Notes

1. **Date Format**: All dates use ISO format (YYYY-MM-DD)
2. **Validation**: Dates are validated against the XML data validity period
3. **Fallback**: When no date is specified, current schedule is used
4. **Error Handling**: Invalid dates return 400 status with helpful error messages
5. **Performance**: Date validation is fast as it only checks against stored validity period

## Testing

Run the test scripts to verify functionality:

```bash
# Test backend date functionality
python test_date_functionality.py

# Test API endpoints (requires Flask app running)
python test_api_date_functionality.py
```

## Benefits

1. **Future Planning**: Users can search trains for future dates within the validity period
2. **Accurate Data**: Only shows trains that actually run on specific dates
3. **User Feedback**: Clear error messages when dates are out of range
4. **Validation**: Prevents invalid API calls with proper date checking
5. **Flexibility**: Works with or without date parameters for backward compatibility
