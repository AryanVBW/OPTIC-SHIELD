# OPTIC-SHIELD Dashboard

Web dashboard for monitoring wildlife detection devices. Built with Next.js and designed for deployment on Vercel.

## Features

- **Real-time Device Monitoring**: View status of all connected devices
- **Detection History**: Browse and filter wildlife detections
- **Analytics**: Detection trends and species distribution
- **Secure API**: JWT-based authentication for device communication

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Edit .env.local with your API secret key
# API_SECRET_KEY=your_secret_key_here

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

### Production Deployment (Vercel)

1. Push code to GitHub
2. Connect repository to Vercel
3. Add environment variables in Vercel dashboard:
   - `API_SECRET_KEY`: Your secret key for device authentication
4. Deploy

```bash
# Or deploy via CLI
vercel deploy --prod
```

## API Endpoints

### Device Registration
```
POST /api/devices
Headers: X-API-Key, X-Device-ID
Body: { device_id, info: { name, location } }
```

### Device Heartbeat
```
POST /api/devices/heartbeat
Headers: X-API-Key, X-Device-ID
Body: { device_id, timestamp, status, stats }
```

### Submit Detection
```
POST /api/devices/detections
Headers: X-API-Key, X-Device-ID
Body: { detection_id, device_id, timestamp, class_name, confidence, bbox, image_base64? }
```

### Batch Detections
```
POST /api/devices/detections/batch
Headers: X-API-Key, X-Device-ID
Body: { device_id, detections: [...] }
```

### Get Detections
```
GET /api/detections?limit=50&device_id=xxx
```

### Get Stats
```
GET /api/stats
```

## Configuration

### Device Configuration

On each Raspberry Pi device, configure the dashboard connection:

```yaml
# device/config/config.prod.yaml
dashboard:
  api_url: "https://your-dashboard.vercel.app/api"
  api_key: "your_api_secret_key"
```

Or via environment variables:
```bash
export OPTIC_DASHBOARD_URL=https://your-dashboard.vercel.app
export OPTIC_API_KEY=your_api_secret_key
```

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Charts**: Recharts
- **Deployment**: Vercel

## License

MIT License
