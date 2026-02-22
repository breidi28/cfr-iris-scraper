import requests
req = requests.get('http://127.0.0.1:5000/api/train/1621')
data = req.json()
stops = data.get('stops', data.get('stations', []))
print(f"Total: {len(stops)}")
print("Stop instances:", sum(1 for s in stops if s.get('is_stop') is not False))
