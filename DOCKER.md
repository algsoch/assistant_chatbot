# 🐳 Docker Deployment Guide for Vicky Chatbot

## Quick Start

### 1. Prerequisites
- Docker and Docker Compose installed
- Environment variables configured

### 2. Setup Environment
```bash
# Copy environment template
cp .env.docker .env

# Edit .env with your actual API keys
# Required: GEMINI_API_KEY, DISCORD_WEBHOOK
# Optional: GITHUB_TOKEN, GITHUB_USERNAME, ADMIN_KEY
```

### 3. Build and Run
```bash
# Using Makefile (recommended)
make build
make run

# Or using docker-compose directly
docker-compose build
docker-compose up -d
```

### 4. Access Application
- **Development**: http://localhost:8000
- **Production** (with nginx): http://localhost

## 🛠️ Available Commands

### Development
```bash
make run        # Run application
make dev        # Run with file watching for development
make logs       # View real-time logs
make shell      # Access container bash
make restart    # Restart application
```

### Production
```bash
make run-prod   # Run with nginx reverse proxy
make health     # Check application health
```

### Maintenance
```bash
make stop       # Stop containers
make clean      # Remove containers and cleanup
make build      # Rebuild images
```

## 📁 File Structure

```
├── Dockerfile              # Main application container
├── docker-compose.yml      # Development setup
├── docker-compose.dev.yml  # Development overrides
├── nginx.conf              # Nginx configuration
├── .dockerignore           # Files to exclude from build
├── .env.docker             # Environment template
└── Makefile                # Easy command shortcuts
```

## 🔧 Configuration

### Environment Variables
- `GEMINI_API_KEY`: Required for AI functionality
- `DISCORD_WEBHOOK`: Required for notifications
- `GITHUB_TOKEN`: Optional for GitHub integration
- `ADMIN_KEY`: Optional for admin access
- `PORT`: Application port (default: 8000)

### Volumes
- `./uploads`: File upload directory
- `./temp_files`: Temporary files
- `./static`: Static assets (read-only in production)
- `./templates`: HTML templates (read-only in production)

## 🚀 Deployment Options

### Local Development
```bash
make dev
```
- File watching enabled
- Source code mounted as volume
- Hot reload on changes

### Production Ready
```bash
make run-prod
```
- Nginx reverse proxy
- Optimized static file serving
- Health checks enabled
- Automatic restart on failure

### Custom Registry
```bash
# Edit Makefile push target with your registry
make push
```

## 🔍 Troubleshooting

### Check Application Health
```bash
make health
curl http://localhost:8000/api/info
```

### View Logs
```bash
make logs
docker-compose logs vicky-app
```

### Debug Container
```bash
make shell
docker-compose exec vicky-app bash
```

### Common Issues

1. **Port 8000 already in use**
   ```bash
   docker-compose down
   make clean
   ```

2. **Environment variables not loaded**
   ```bash
   # Check .env file exists and has correct values
   cat .env
   ```

3. **Build failures**
   ```bash
   make clean
   make build
   ```

## 📊 Performance

- **Multi-worker**: 4 Gunicorn workers by default
- **Health checks**: Built-in application monitoring
- **Timeout**: 120 seconds for long-running requests
- **File uploads**: 50MB maximum size
- **Compression**: Gzip enabled for static files

## 🔒 Security

- Non-root user in container
- Minimal base image (Python slim)
- Environment variable isolation
- Nginx security headers (in production)
- File upload restrictions
