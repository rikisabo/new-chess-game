# 🚀 Chess Game Server - Railway Deployment Guide

## Quick Deploy to Railway

### Method 1: GitHub Integration (Recommended)

1. **Push to GitHub:**
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

2. **Connect to Railway:**
- Go to [railway.app](https://railway.app)
- Sign up with GitHub account
- Click "Deploy from GitHub repo"
- Select your `new-chess-game` repository
- Railway will auto-detect the project

3. **Environment Variables:**
Railway will automatically set:
- `PORT` (provided by Railway)
- `HOST=0.0.0.0` (required for Railway)

### Method 2: Railway CLI

1. **Install Railway CLI:**
```bash
npm install -g @railway/cli
# or
curl -fsSL https://railway.app/install.sh | sh
```

2. **Login and Deploy:**
```bash
railway login
railway init
railway up
```

## 📋 Deployment Checklist

- [x] Server configured for Railway (HOST=0.0.0.0, PORT from env)
- [x] Dockerfile optimized for production
- [x] railway.json configuration file
- [x] requirements.txt updated
- [x] main.py entry point created
- [x] Logging configured for production

## 🔗 Expected URLs

After deployment, you'll get:
- **Server URL**: `https://your-app-name.railway.app`
- **WebSocket URL**: `wss://your-app-name.railway.app`

## 🧪 Testing Deployment

1. **Local Test (before deploy):**
```bash
cd server
PORT=8000 HOST=0.0.0.0 python main.py
```

2. **After Deployment:**
- Use the WebSocket URL in your client
- Test with your existing Python client

## 🔧 Common Issues

### Build Fails
- Check `requirements.txt` has all dependencies
- Ensure Dockerfile uses correct Python version

### Connection Issues  
- Verify WebSocket URL uses `wss://` (not `ws://`)
- Check Railway logs for errors

### Memory Issues
- Railway free tier: 512MB RAM
- Monitor usage in Railway dashboard

## 📊 Production Features

Your deployed server includes:
- Multi-game architecture
- Auto-scaling WebSocket connections
- Production logging
- Environment-based configuration
- Docker containerization
- Automatic HTTPS/WSS

## 💡 Next Steps

1. Deploy server to Railway
2. Update client with production WebSocket URL
3. Create distribution package for desktop client
4. Optional: Create simple web landing page
