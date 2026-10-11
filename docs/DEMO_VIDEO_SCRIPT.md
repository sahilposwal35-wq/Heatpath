# HeatPath — 3-Minute Hackathon Demo Video Script
**Track 02: Heat & Water | WeMakeDevs Environmental Hacks**

> **Target Duration:** ~2 minutes 40 seconds (Strict limit: < 3 minutes)  
> **Format:** YouTube (Unlisted or Public)  
> **Live Demo URL:** `http://15.134.223.130`  
> **Repository:** [https://github.com/sahilposwal35-wq/Heatpath](https://github.com/sahilposwal35-wq/Heatpath)

---

## 🎬 Recording Setup & Preparation

Before hitting record, have these 3 tabs open in your browser:
1. **Tab 1:** Live HeatPath App (`http://15.134.223.130`) — Clean full-screen view.
2. **Tab 2:** AWS EC2 Console — Showing `heatpath-server` in **Running** state with IP `15.134.223.130` in `ap-south-1 (Mumbai)`.
3. **Tab 3:** GitHub Repository (`https://github.com/sahilposwal35-wq/Heatpath`) or Swagger Docs (`http://15.134.223.130:8000/docs`).

---

## ⏱️ Video Timeline Overview

| Section | Timestamp | Duration | Focus Area |
|---|---|---|---|
| **1. Hook & About the Project** | 0:00 – 0:40 | 40s | Problem statement, Indian urban heat, HeatPath solution |
| **2. Live Demo & Key Features** | 0:40 – 1:30 | 50s | Place autocomplete, route comparison, heat metrics |
| **3. Tech Stack & Architecture** | 1:30 – 2:05 | 35s | FastAPI, React, Leaflet, Valhalla, Open-Meteo, Scoring Model |
| **4. How We Used AWS** | 2:05 – 2:35 | 30s | Live EC2 deployment in Mumbai, Docker, CloudWatch |
| **5. Learning & Conclusion** | 2:35 – 2:50 | 15s | Takeaways, impact, wrap-up |

---

## 📝 Word-for-Word Script & Screen Actions

### [0:00 – 0:40] 1. About the Project (Problem & Vision)

**🖥️ On Screen:**
- Start on **Tab 1 (`http://15.134.223.130`)**.
- Show the clean HeatPath interface with the Pune map loaded.

**🎙️ What to Say:**
> *"Hello everyone! In Indian cities like Pune, summer temperatures frequently exceed 40 degrees Celsius. While navigation apps like Google Maps always recommend the absolute shortest walking path, they completely ignore extreme heat exposure. A pedestrian taking that route might walk directly under intense midday sunlight with zero shade, risking severe heat exhaustion.*
> 
> *To solve this, we built **HeatPath** — a heat-aware pedestrian navigation system. HeatPath doesn't just find the fastest way from point A to point B; it models microclimate temperature, solar irradiance, and tree canopy to calculate a heat-optimized walking alternative that keeps pedestrians safe."*

---

### [0:40 – 1:30] 2. Live Product Demonstration

**🖥️ On Screen:**
- Click the **Start Location** search bar. Type `FC Road` and select `Fergusson College Road` from the autocomplete dropdown. Notice the map smooth-pans to it.
- Click the **Destination** search bar. Type `Shaniwar Wada` and select it.
- Click **"Find Heat-Aware Routes"**.
- Point your mouse at the route cards on the left and the colored polyline routes on the map.
- Click on the **"Recommended (Heat-Optimized)"** route card to show the comparison.

**🎙️ What to Say:**
> *"Let’s see it in action on our live deployment. HeatPath features instant Google Maps-style place search. Let's enter Fergusson College Road as our origin, and Shaniwar Wada as our destination in central Pune.*
> 
> *With one click, HeatPath queries real routing networks and real-time atmospheric data. As you can see, it presents two distinct options:*
> 
> *First, the **Fastest Route** — which takes 24 minutes, but exposes the walker to an elevated heat index with continuous direct sunlight.*
> 
> *Second, our **Recommended Heat-Optimized Route** — which trades just 2 extra minutes of walking for a massive 35% reduction in cumulative heat exposure. The app breaks down real-time ambient temperature, solar angle, shade percentage, and even provides actionable hydration and rest guidance."*

---

### [1:30 – 2:05] 3. Tech Stack & Architecture

**🖥️ On Screen:**
- Briefly switch to **Tab 3 (`http://15.134.223.130:8000/docs`)** or your GitHub repo structure.
- Scroll down to show the clean FastAPI endpoints (`/api/routes`, `/api/geocode`, `/health`).

**🎙️ What to Say:**
> *"Behind the scenes, HeatPath is built with a production-grade architecture:*
> 
> *On the frontend, we use **React, TypeScript, Vite, and Leaflet** with dark-mode OpenStreetMap tiles for responsive mapping.*
> 
> *On the backend, we run **FastAPI with Python 3.12**. It integrates with the **Valhalla OpenStreetMap routing engine** for pedestrian paths, and the **Open-Meteo weather API** for localized hourly heat indices and solar elevation.*
> 
> *Our custom multi-factor scoring model balances travel time, shade coverage, and solar radiation to produce transparent, explainable recommendations without treating routing as a black box."*

---

### [2:05 – 2:35] 4. How We Used AWS

**🖥️ On Screen:**
- Switch to **Tab 2 (AWS EC2 Console)**.
- Highlight the instance `heatpath-server` running in `ap-south-1 (Asia Pacific - Mumbai)` with public IP `15.134.223.130`.
- Briefly mention Docker Compose running both containers.

**🎙️ What to Say:**
> *"For cloud deployment, HeatPath is deployed live on **Amazon Web Services** in the **Asia Pacific (Mumbai) region `ap-south-1`**, ensuring ultra-low latency for users in India.*
> 
> *We containerized both frontend and backend using **Docker** and orchestrated them via **Docker Compose** on an Amazon EC2 instance. An **Nginx reverse proxy** serves the production web bundle on port 80 and securely proxies API traffic.*
> 
> *We also configured **AWS CloudWatch** integration to stream application logs and track routing query telemetry in real time — all while keeping costs well under $2, preserving over 98% of our $100 hackathon credits."*

---

### [2:35 – 2:50] 5. Learning & Growth & Closing

**🖥️ On Screen:**
- Switch back to **Tab 1 (`http://15.134.223.130`)** showing the active route comparison.

**🎙️ What to Say:**
> *"Building HeatPath was an incredible learning experience in geospatial data pipelines, combining real-time meteorology with street network graphs, and building scalable cloud containers on AWS.*
> 
> *HeatPath proves that urban mobility can be healthier, smarter, and climate-resilient. Thank you to WeMakeDevs and AWS for organizing this hackathon!"*

---

## 💡 Quick Tips for a High-Scoring Video
1. **Speak clearly at a steady pace**: Don't rush; the script is timed at ~130 words per minute, which comfortably fits within 2:40.
2. **Move the mouse deliberately**: When talking about a feature (like the heat score reduction or the AWS IP), hover your cursor directly over it so the judges immediately see it.
3. **Resolution**: Record in 1080p (Full HD) if possible.
4. **YouTube Settings**: Upload as **Unlisted** (or Public) and ensure the link is tested in an incognito window before submitting.
