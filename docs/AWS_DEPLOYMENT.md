# HeatPath — AWS Deployment Guide ($100 Credit Budget)

This guide provides step-by-step instructions for deploying HeatPath to AWS for the **WeMakeDevs Environmental Hacks (Track 02: Heat & Water)** hackathon.

---

## 1. Cost & Architecture Overview (Budget: < $3 from your $100 Credits)

We have two battle-tested deployment paths that satisfy all hackathon criteria ("AWS usage visible in demo", public URL, and CloudWatch telemetry):

| Deployment Component | Recommended Architecture (Serverless / Managed) | Alternative (Single EC2) |
|---|---|---|
| **Backend API** | **AWS App Runner** (Auto-managed container + HTTPS) | **Amazon EC2** (`t3.small` / `t3.micro` in `ap-south-1`) |
| **Frontend UI** | **Amazon S3 Static Website** + **CloudFront CDN** | Served directly via Nginx on EC2 |
| **Observability** | **Amazon CloudWatch Logs** (`/heatpath/backend`) | **Amazon CloudWatch Agent** / Docker logs |
| **Estimated Cost** | **~$1.00 – $2.50 total** for entire hackathon | **~$1.50 total** ($0.02/hr) |

Both architectures keep > 97% of your $100 credit intact.

---

## Architecture Option 1: AWS App Runner + S3 & CloudFront (Recommended)

This gives you a dedicated HTTPS link (`https://*.awsapprunner.com`) for the backend without having to manage Linux servers or configure SSL certificates manually.

### Step 1: Push Backend Container to Amazon ECR
1. Open the [AWS Console](https://console.aws.amazon.com/) → **Amazon ECR** → **Create repository**:
   - Repository name: `heatpath-backend`
   - Visibility: **Private**
2. In your local terminal, log in to ECR and push the Docker image:
   ```bash
   # Replace <ACCOUNT_ID> and <REGION> (e.g. ap-south-1)
   aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com

   # Build and tag container
   cd /home/elliot/Downloads/Wemakedevs/heatpath/backend
   docker build -t heatpath-backend .
   docker tag heatpath-backend:latest <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/heatpath-backend:latest

   # Push to ECR
   docker push <ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/heatpath-backend:latest
   ```

### Step 2: Deploy on AWS App Runner
1. Go to **AWS App Runner** in AWS Console → **Create service**.
2. **Source**: Container registry → **Amazon ECR** → Browse and select `heatpath-backend:latest`.
3. **Deployment settings**: Automatic or Manual.
4. **Service settings**:
   - Service name: `heatpath-api`
   - Port: `8000`
   - CPU: `1 vCPU`, Memory: `2 GB`
   - Environment variables (Add from `backend/.env`):
     - `VALHALLA_BASE_URL` = `https://valhalla1.openstreetmap.de`
     - `OPEN_METEO_BASE_URL` = `https://api.open-meteo.com/v1`
     - `PILOT_TIMEZONE` = `Asia/Kolkata`
     - `AWS_CLOUDWATCH_LOG_GROUP` = `/heatpath/backend`
5. Click **Create & Deploy**. In ~3 minutes, App Runner will give you a public HTTPS URL:
   `https://xxxxxx.ap-south-1.awsapprunner.com`.
6. Test your live endpoint: `https://xxxxxx.ap-south-1.awsapprunner.com/health`.

### Step 3: Build & Deploy Frontend to Amazon S3
1. Set the live API URL in `frontend/.env`:
   ```ini
   VITE_API_BASE_URL=https://xxxxxx.ap-south-1.awsapprunner.com
   ```
2. Build the production assets:
   ```bash
   cd /home/elliot/Downloads/Wemakedevs/heatpath/frontend
   npm run build
   ```
3. Create an S3 Bucket (e.g. `heatpath-app-demo`):
   ```bash
   aws s3 mb s3://heatpath-app-demo --region ap-south-1
   aws s3 sync dist/ s3://heatpath-app-demo --acl public-read
   aws s3 website s3://heatpath-app-demo --index-document index.html
   ```
   *(Or connect Amazon CloudFront to the S3 bucket for global HTTPS distribution).*

---

## Architecture Option 2: Single Amazon EC2 Instance (Fastest & Simplest)

If you prefer launching a standard Linux VM:

### Step 1: Launch EC2 Instance
1. AWS Console → **EC2** → **Launch Instance**:
   - Name: `heatpath-pilot`
   - AMI: Ubuntu 24.04 LTS (64-bit x86)
   - Instance type: `t3.small` (2 vCPU, 2 GB RAM) or `t3.micro`
   - Key pair: Create or select your `.pem` key
   - Security Group: Allow **HTTP (Port 80)**, **Custom TCP (Port 8000)**, and **SSH (Port 22)** from anywhere (`0.0.0.0/0`).
2. Launch instance.

### Step 2: Deploy with Docker Compose on EC2
1. SSH into the instance:
   ```bash
   ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
   ```
2. Install Docker:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-v2 git
   sudo usermod -aG docker ubuntu
   newgrp docker
   ```
3. Clone repo or copy `heatpath` folder to EC2:
   ```bash
   git clone <YOUR_PUBLIC_GITHUB_REPO_URL> heatpath
   cd heatpath
   ```
4. Start both backend & frontend with one command:
   ```bash
   docker compose up -d --build
   ```
5. Open `http://<EC2_PUBLIC_IP>` in your browser — your entire application is live!

---

## 3. Demonstrating AWS in Your Demo Video (Judges Criteria)

To score maximum marks for the AWS criteria in Track 02:
1. **Show the AWS Console**:
   - Open AWS Console in your browser during the video.
   - Show the running **App Runner service** or **EC2 instance** in `ap-south-1 (Mumbai)`.
2. **Show CloudWatch Logs**:
   - Open **CloudWatch** → **Log groups** → `/heatpath/backend`.
   - Show live logs recording a route calculation with exposure scores and metrics.
3. **Show the Live URL**:
   - Navigate to the deployed frontend and run a route comparison query on screen.
