# Deployment Guide

## Quick Deploy to Render (Recommended - Free Tier)

### Option 1: One-Click Deploy (Easiest)

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to [render.com](https://render.com) and sign up/login
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml` configuration
   - Click "Apply" to use the Blueprint

3. **Set Environment Variables**
   - In Render dashboard, go to your service
   - Navigate to "Environment" tab
   - Add your `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
   - Save changes (will auto-redeploy)

4. **Done!** Your app will be live at `https://disha-ai.onrender.com` (or similar)

### Option 2: Manual Setup on Render

If you don't want to use GitHub or prefer manual setup:

1. **Create Web Service**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Choose "Build and deploy from a Git repository"

2. **Configure Build Settings**
   - **Build Command**: `pip install -r requirements.txt && python init_db.py`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3

3. **Environment Variables** (Add these in Render dashboard)
   ```
   OPENAI_API_KEY=your-key-here
   LLM_PROVIDER=openai
   DATABASE_URL=sqlite:///./disha_ai.db
   ENVIRONMENT=production
   ```

4. **Deploy** - Render will build and deploy automatically

### Persistent Database Note

⚠️ Render's free tier has ephemeral storage - your SQLite database will reset on redeploys.

**Solutions:**
1. Upgrade to Render's paid plan ($7/month) for persistent disks
2. Use PostgreSQL instead of SQLite (Render provides free 90-day PostgreSQL)
3. Use an external database service

## Alternative Deployments

### Railway (Also Free, Better for SQLite)

1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Railway auto-detects Python and deploys
5. Add environment variables in dashboard
6. Railway provides persistent storage even on free tier!

### Fly.io (Good for Global Deployment)

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Create `fly.toml`:
   ```toml
   app = "disha-ai"
   
   [build]
     builder = "paketobuildpacks/builder:base"
   
   [[services]]
     internal_port = 8000
     protocol = "tcp"
   
     [[services.ports]]
       port = 80
       handlers = ["http"]
     [[services.ports]]
       port = 443
       handlers = ["tls", "http"]
   ```
4. Deploy: `fly launch` then `fly deploy`

### Heroku (Classic, $5/month after free trial ends)

1. Create `Procfile`:
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
2. Install Heroku CLI and login
3. Deploy:
   ```bash
   heroku create disha-ai
   heroku config:set OPENAI_API_KEY=your-key
   git push heroku main
   ```

## Using PostgreSQL Instead of SQLite (Recommended for Production)

If you switch to PostgreSQL for production:

1. **Update requirements.txt** (already includes `psycopg2-binary`)

2. **Update DATABASE_URL** in environment:
   ```
   DATABASE_URL=postgresql://user:password@host:5432/dbname
   ```

3. **No code changes needed** - SQLAlchemy handles everything!

## Monitoring Your Deployment

- **Render**: Check logs in dashboard under "Logs" tab
- **Railway**: Click on service → "View Logs"
- **Health Check**: Visit `https://your-app.com/health`

## Common Deployment Issues

### 1. "Module not found" error
- Make sure all dependencies are in `requirements.txt`
- Check build logs for failed installations

### 2. "Database locked" error with SQLite
- SQLite doesn't handle concurrent writes well
- Consider PostgreSQL for production

### 3. API Key not working
- Double-check environment variable name matches exactly
- Some platforms need restart after adding env vars

### 4. App sleeps/shuts down (Free Tier)
- Most free tiers sleep after inactivity
- Use cron jobs or uptime monitors to keep alive
- Or upgrade to paid tier

## Cost Comparison

| Platform | Free Tier | Paid Tier | Persistent DB |
|----------|-----------|-----------|---------------|
| Render | 750 hrs/mo | $7/mo | Paid only |
| Railway | 500 hrs/mo + $5 credit | $5/mo | Yes (free) |
| Fly.io | 3 VMs free | $1.94/mo | Paid only |
| Heroku | Trial only | $5/mo | Add-on req |

**Recommendation**: Start with **Railway** for free tier with persistent storage, or **Render** if you're okay with resets.

## Security Checklist for Production

- [ ] Set strong OPENAI_API_KEY
- [ ] Set ENVIRONMENT=production
- [ ] Don't commit .env file to Git
- [ ] Enable HTTPS (automatic on most platforms)
- [ ] Add rate limiting (future TODO)
- [ ] Update CORS origins to specific domain
- [ ] Add authentication (future TODO)

## Post-Deployment

Once deployed, update your `README.md` with:
```markdown
## Live Demo
🌐 **Live at**: https://your-app.onrender.com
```

Test your deployment:
```bash
# Health check
curl https://your-app.onrender.com/health

# API docs
open https://your-app.onrender.com/docs
```

---

**Need help?** Check platform-specific documentation:
- [Render Docs](https://render.com/docs)
- [Railway Docs](https://docs.railway.app)
- [Fly.io Docs](https://fly.io/docs)
