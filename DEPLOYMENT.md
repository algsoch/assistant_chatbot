# Deployment Guide

## Deploy to Render

### Prerequisites
- GitHub account
- Render account (free)
- Your environment variables ready

### Steps for Render Deployment

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Create Render Service**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Choose "vicky-chatbot-app" repository

3. **Configure Environment Variables**
   Add these environment variables in Render dashboard:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   DISCORD_WEBHOOK=your_discord_webhook_url
   GITHUB_TOKEN=your_github_token
   GITHUB_USERNAME=your_github_username
   ADMIN_KEY=your_admin_key
   PORT=8000
   ```

4. **Deploy**
   - Render will automatically detect the `render.yaml` file
   - Click "Create Web Service"
   - Wait for build and deployment (5-10 minutes)

### Deploy to Vercel (Alternative)

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Deploy**
   ```bash
   vercel --prod
   ```

3. **Configure Environment Variables**
   Set the same environment variables in Vercel dashboard

## Important Files for Deployment

- `requirements.txt` - Python dependencies
- `Procfile` - Gunicorn server configuration
- `render.yaml` - Render-specific configuration
- `runtime.txt` - Python version specification
- `.gitignore` - Excludes sensitive files
- `.env.example` - Template for environment variables

## Health Check

Your app will be available at:
- Health check: `https://your-app.onrender.com/api/info`
- Main app: `https://your-app.onrender.com`
- API docs: `https://your-app.onrender.com/docs`

## Troubleshooting

1. **Build fails**: Check `requirements.txt` for incompatible versions
2. **App crashes**: Check environment variables are set correctly
3. **API errors**: Verify GEMINI_API_KEY has correct permissions
4. **GitHub integration fails**: Ensure GITHUB_TOKEN has repo access
