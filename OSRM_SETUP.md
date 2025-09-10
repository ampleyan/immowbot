# OSRM Local Server Setup for Belgium

This guide helps you set up a local OSRM server with Belgium OSM data for accurate cycling and walking routes.

## 🚀 Quick Setup

### 1. Download Belgium OSM Data
```bash
# Download Belgium data (~84MB)
wget http://download.geofabrik.de/europe/belgium-latest.osm.pbf
# or use curl on Windows
curl -O http://download.geofabrik.de/europe/belgium-latest.osm.pbf
```

### 2. Setup OSRM with Docker

**Method 1: Single Server (Easier Setup)**
```bash
# Create osrm directory and place Belgium data there
mkdir osrm
cp belgium-latest.osm.pbf osrm/

# Extract, partition, and customize with bicycle profile
docker run -t -v $(pwd)/osrm:/data osrm/osrm-backend osrm-extract -p /opt/bicycle.lua /data/belgium-latest.osm.pbf
docker run -t -v $(pwd)/osrm:/data osrm/osrm-backend osrm-partition /data/belgium-latest.osrm
docker run -t -v $(pwd)/osrm:/data osrm/osrm-backend osrm-customize /data/belgium-latest.osrm

# Start server on port 5000
docker run -t -i -p 5000:5000 -v $(pwd)/osrm:/data osrm/osrm-backend osrm-routed --algorithm mld /data/belgium-latest.osrm
```

**Method 2: Dual Server (More Accurate - Advanced)**
```bash
# Setup cycling server (port 5000)
mkdir osrm-bike && cp belgium-latest.osm.pbf osrm-bike/
docker run -t -v $(pwd)/osrm-bike:/data osrm/osrm-backend osrm-extract -p /opt/bicycle.lua /data/belgium-latest.osm.pbf
docker run -t -v $(pwd)/osrm-bike:/data osrm/osrm-backend osrm-partition /data/belgium-latest.osrm
docker run -t -v $(pwd)/osrm-bike:/data osrm/osrm-backend osrm-customize /data/belgium-latest.osrm
docker run -d -p 5000:5000 -v $(pwd)/osrm-bike:/data osrm/osrm-backend osrm-routed --algorithm mld /data/belgium-latest.osrm

# Setup walking server (port 5001)
mkdir osrm-walk && cp belgium-latest.osm.pbf osrm-walk/
docker run -t -v $(pwd)/osrm-walk:/data osrm/osrm-backend osrm-extract -p /opt/foot.lua /data/belgium-latest.osm.pbf
docker run -t -v $(pwd)/osrm-walk:/data osrm/osrm-backend osrm-partition /data/belgium-latest.osrm
docker run -t -v $(pwd)/osrm-walk:/data osrm/osrm-backend osrm-customize /data/belgium-latest.osrm
docker run -d -p 5001:5000 -v $(pwd)/osrm-walk:/data osrm/osrm-backend osrm-routed --algorithm mld /data/belgium-latest.osrm
```

**How It Works:**
- 🚗 **Driving**: Uses reliable public server (always available, well-maintained)
- 🚴 **Cycling**: Uses your local server with Belgium bike lanes and cycle paths
- 🚶 **Walking**: 
  - Method 1: Uses cycling routes + walking speed adjustments (simpler)
  - Method 2: Uses dedicated walking server with pedestrian-only paths (more accurate)

### 3. Test Your Setup
```bash
**Method 1 Testing:**
```bash
# Test cycling route
curl "http://localhost:5000/route/v1/cycling/4.3909,51.2018;4.3952,51.2120?overview=false"

# Test walking route (may return same as cycling - system will apply speed adjustments)
curl "http://localhost:5000/route/v1/foot/4.3909,51.2018;4.3952,51.2120?overview=false"
```

**Method 2 Testing:**
```bash
# Test cycling server
curl "http://localhost:5000/route/v1/cycling/4.3909,51.2018;4.3952,51.2120?overview=false"

# Test walking server
curl "http://localhost:5001/route/v1/foot/4.3909,51.2018;4.3952,51.2120?overview=false"
```

**Note**: Driving will automatically use public server (no local setup needed)
```

## 🔧 Windows PowerShell Commands

```powershell
# Download data
Invoke-WebRequest -Uri "http://download.geofabrik.de/europe/belgium-latest.osm.pbf" -OutFile "belgium-latest.osm.pbf"

# Create directory and move file
New-Item -ItemType Directory -Path "osrm" -Force
Move-Item "belgium-latest.osm.pbf" "osrm/"

# Docker commands for cycling/walking server
docker run -t -v ${PWD}/osrm:/data osrm/osrm-backend osrm-extract -p /opt/bicycle.lua /data/belgium-latest.osm.pbf
docker run -t -v ${PWD}/osrm:/data osrm/osrm-backend osrm-partition /data/belgium-latest.osrm  
docker run -t -v ${PWD}/osrm:/data osrm/osrm-backend osrm-customize /data/belgium-latest.osrm
docker run -t -i -p 5000:5000 -v ${PWD}/osrm:/data osrm/osrm-backend osrm-routed --algorithm mld /data/belgium-latest.osrm
```

## ✅ What This Hybrid Approach Gives You

### **Hybrid Setup Benefits:**
- 🚗 **Driving**: Reliable public server (always works, no maintenance)
- 🚴 **Cycling**: Local Belgium data with real bike lanes and cycle paths
- 🚶 **Walking**: Local Belgium data with pedestrian paths and park shortcuts
- 🔄 **Smart Fallback**: If local server is down, uses speed adjustments
- ⚡ **Best of Both**: Reliability + Accuracy where it matters most

## 🎯 Integration with Immowbot

The system **automatically detects** your local OSRM server:

```python
# When you run analysis with local server, you'll see:
✅ Local OSRM server detected - using Belgium OSM data for cycling/walking routes!
ℹ️  Driving routes will use reliable public server

# Or if no local server:
ℹ️  No local OSRM server found - using speed adjustments for cycling/walking
ℹ️  Driving routes will use public server
```

## 📊 Expected Improvements

**Before:**
```
Car: 8min, 4.7km
Bike: 8min, 4.7km    # Same as car (wrong!)
Walk: 8min, 4.7km    # Same as car (wrong!)
```

**After:**
```
Car: 8min, 4.7km     # Via fastest car route
Bike: 12min, 4.2km   # Via bike lanes and cycle paths
Walk: 32min, 3.8km   # Via pedestrian paths and shortcuts
```

## 🐛 Troubleshooting

**Docker Issues:**
- Make sure Docker is running
- Check port 5000 isn't already in use: `netstat -an | findstr 5000`

**Memory Issues:**
- Belgium processing needs ~4GB RAM
- Close other applications during setup

**File Permissions (Linux/Mac):**
- Make sure docker can access the OSM file: `chmod 644 belgium-latest.osm.pbf`

The local OSRM server will give you **much more accurate** travel times and distances using real Belgian cycling and walking infrastructure!