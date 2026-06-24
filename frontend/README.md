# Crystal Supplier Email Service - Frontend

This is the frontend application for the Crystal Supplier Email Service, built with React, Vite, and Tailwind CSS. It provides an intuitive dashboard to manage RFQ campaigns, track supplier responses, and view AI-extracted insights.

## Technologies Used
- **React 19**: UI library
- **Vite**: Build tool and development server
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Icon library

## Getting Started

### Prerequisites
Make sure you have Node.js (v18+) and npm installed.

### Installation
```bash
npm install
```

### Development Server
```bash
npm run dev
```
The application will be available at `http://localhost:5173`. Ensure the FastAPI backend is also running concurrently to supply data to the application.

## Production Docker Build
Build the frontend container from the `frontend/` directory:

```bash
docker build -t crystal-frontend .
docker run --rm -p 8080:8080 crystal-frontend
```

The container serves the Vite production build on `http://localhost:8080`. The runtime process binds to Cloud Run's `PORT` environment variable automatically, and the API base URL is baked in at build time from `.env.production`.

## Deploy To Cloud Run
From the repository root, deploy the frontend as a separate Cloud Run service:

```bash
gcloud run deploy crystal-supplier-email-frontend \
	--source frontend \
	--region asia-south1 \
	--allow-unauthenticated
```

That build uses `frontend/Dockerfile`, serves the static bundle on the `PORT` provided by Cloud Run, and uses `.env.production` so API requests target the deployed backend.

## Features
- **Campaign Dashboard**: View active and closed jobs.
- **Supplier Tracking**: Monitor real-time status of supplier replies and reminder emails.
- **Insights View**: Examine data extracted automatically from supplier responses using Google Generative AI.
- **Responsive Design**: Clean layout powered by Tailwind CSS.
