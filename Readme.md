⚓ NexusAZ: Just-in-Time Vessel Arrival System
Developed for: AZCON Holding Hackathon  
Focus: Maritime Logistics, Fuel Optimization, and Emission Reduction  
Tech Stack: FastAPI, React, PostgreSQL/PostGIS, WebSockets, Leaflet.js
🌟 Overview
NexusAZ is an intelligent navigation and synchronization platform designed to eliminate the "Speed-to-Wait" problem in maritime logistics. By synchronizing Baku Port terminal availability with real-time vessel AIS data, NexusAZ calculates the Optimal Arrival Speed (JIT). 
This ensures ships arrive exactly when their berth is ready, significantly reducing fuel consumption, engine wear, and carbon emissions.
🚀 Key Features
• Live Vessel Tracking: Real-time map visualization using Leaflet.js and WebSocket streams.
• JIT Optimization Engine: A Python-based algorithm that calculates speed recommendations based on port congestion and distance.
• Dynamic Status Indicators: - 🟢 Optimal: Vessel is on track for a JIT arrival.
  - 🔴 Over-Speed: Vessel is wasting fuel; recommendation to slow down is sent to the captain.
• ESG Dashboard: Live analytics tracking total fuel saved (Liters) and CO2 reduction (%) across the fleet.
• Cybersecurity Layer: JWT authentication and AIS data integrity validation to prevent spoofing.
🛠 Tech Stack
| Component | Technology |
| :--- | :--- |
| Backend | Python, FastAPI |
| Database | PostgreSQL + PostGIS (Spatial queries) |
| Frontend | React.js, Tailwind CSS |
| Maps | Leaflet.js (CartoDB Dark Matter tiles) |
| Real-time | WebSockets (bi-directional communication) |
| Data Simulation | Mock Spire API AIS Stream |
📐 Architecture
NexusAZ follows a hardware-agnostic, modular architecture:
Data Ingestion: Collects AIS telemetry (MMSI, SOG, Lat/Lon).
Processing: The JIT Engine compares telemetry with Port Booking schedules.
Distribution: Updates are broadcasted via WebSockets to the Frontend.
Visualization: Captains and Port Managers see synchronized, actionable data.
📦 Installation & Setup
Prerequisites
• Python 3.9+
• Node.js & npm
• PostgreSQL with PostGIS extension
Backend Setup
Navigate to /backend
Install dependencies: pip install -r requirements.txt
Run the server: uvicorn main:app --reload
Frontend Setup
Navigate to /frontend
Install dependencies: npm install
Start the app: npm run dev
📊 Impact Metrics
 Fuel Savings: Up to 18% per voyage.
 Emissions: Direct reduction in Maritime Carbon Intensity Indicator (CII) ratings.
 Port Efficiency: 30% reduction in port basin congestion and anchoring time.
👥 The Team
• Frontend: [Name]
• Backend: [Name]
• Data/ML: [Name]
• Cybersecurity: [Name]
Created for the AZCON 2024 Hackathon. NexusAZ - Navigating the Future of Sustainable Shipping.*
this is my idea and i wanna to create the web app for this and i am vibe coder and using the windsurf for buildin this app the first give me the prompt about the db sturucture which one is i wrote te windsurf ai