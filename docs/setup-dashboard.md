# Dashboard Deployment Guide

Guide for deploying the OPTIC-SHIELD dashboard to Vercel.

## Prerequisites

- Node.js 18+ installed
- Vercel account
- GitHub account (for automatic deployments)

## Local Development

### 1. Install Dependencies

```bash
cd OPTIC-SHIELD/dashboard
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env.local
```

Edit `.env.local`:
```
API_SECRET_KEY=your_development_secret_key
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Vercel Deployment

### Option 1: GitHub Integration (Recommended)

1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com) and sign in
3. Click "New Project"
4. Import your GitHub repository
5. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `dashboard`
6. Add Environment Variables:
   - `API_SECRET_KEY`: Your secret key for device authentication
7. Click "Deploy"

### Option 2: Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
cd dashboard
vercel

# For production
vercel --prod
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `API_SECRET_KEY` | Secret key for device authentication | Yes |
| `DATABASE_URL` | Database connection string (optional) | No |

## Connecting Devices

After deployment, configure each Raspberry Pi device:

### 1. Get Your Dashboard URL

Your Vercel deployment URL will be something like:
- `https://optic-shield.vercel.app`
- Or your custom domain

### 2. Generate API Key

Use the same `API_SECRET_KEY` you set in Vercel environment variables.

### 3. Configure Device

On each Raspberry Pi, edit the configuration:

```bash
nano ~/OPTIC-SHIELD/device/config/.env
```

Set:
```
OPTIC_API_KEY=your_api_secret_key
OPTIC_DASHBOARD_URL=https://your-dashboard.vercel.app
```

Or edit `config/config.prod.yaml`:
```yaml
dashboard:
  api_url: "https://your-dashboard.vercel.app/api"
  api_key: "your_api_secret_key"
```

### 4. Restart Device Service

```bash
sudo systemctl restart optic-shield
```

## Custom Domain

1. Go to your Vercel project settings
2. Navigate to "Domains"
3. Add your custom domain
4. Update DNS records as instructed
5. Update device configurations with new domain

## Monitoring

### Vercel Dashboard

- View deployment logs
- Monitor function invocations
- Check error rates

### Application Logs

View logs in Vercel dashboard under "Logs" tab.

## Scaling Considerations

For production deployments with many devices:

1. **Database**: Add a database (Vercel Postgres, PlanetScale, etc.)
2. **Caching**: Implement Redis for session/data caching
3. **Rate Limiting**: Add rate limiting for API endpoints
4. **Monitoring**: Set up error tracking (Sentry, etc.)

## Troubleshooting

### Devices Not Connecting

1. Check API key matches between dashboard and device
2. Verify dashboard URL is correct (include https://)
3. Check device logs: `journalctl -u optic-shield -f`

### Build Failures

1. Check Node.js version (18+ required)
2. Run `npm run build` locally to see errors
3. Check Vercel build logs

### API Errors

1. Verify environment variables are set in Vercel
2. Check function logs in Vercel dashboard
3. Test API endpoints with curl:

```bash
curl -X POST https://your-dashboard.vercel.app/api/devices/heartbeat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -H "X-Device-ID: test-device" \
  -d '{"device_id": "test", "timestamp": 1234567890, "status": "online"}'
```
