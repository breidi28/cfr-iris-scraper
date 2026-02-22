import requests
from bs4 import BeautifulSoup
import json

train_id = "1621"
url = f"https://mersultrenurilor.infofer.ro/ro-RO/Tren/{train_id}"
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.content, 'html.parser')

# Let's see if there are any sections with stops
direction_section = soup.find(string=lambda text: text and 'Direc' in text)
print("Direction section elements:")
if direction_section:
    parent = direction_section.parent
    while parent and parent.name != 'body':
        print(f"Parent {parent.name} class {parent.get('class')}")
        if 'card' in parent.get('class', []):
            print(parent.get_text(separator=' | ', strip=True))
            break
        parent = parent.parent

# Let's find all station names on the main page.
links = soup.find_all('a', href=lambda x: x and '/ro-RO/Statie/' in x)
print("\nUnique stations in links:")
stations = []
import re
for link in links:
    text = link.get_text(strip=True)
    if text and text not in stations:
        stations.append(text)
print(stations)
