#!/bin/bash

# Deployment Setup Script for Render and GitHub

echo "🚀 Setting up deployment for TDS - Tools for Data Science"
echo "=============================================="

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not in a git repository. Initializing..."
    git init
    git remote add origin https://github.com/algsoch/chatbot_tds.git
fi

# Ensure all required files exist
echo "📋 Checking deployment files..."

files=(
    "requirements.txt"
    "Procfile"
    "render.yaml"
    "runtime.txt"
    ".gitignore"
    ".env.example"
    "vicky_app.py"
    "vicky_server.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

# Check environment variables
echo ""
echo "🔧 Environment Variables Required:"
echo "- GEMINI_API_KEY (Google Gemini API)"
echo "- DISCORD_WEBHOOK (Discord notifications)"
echo "- GITHUB_TOKEN (GitHub integration)"
echo "- GITHUB_USERNAME (GitHub username)"
echo "- ADMIN_KEY (Admin access)"

echo ""
echo "📝 Next Steps:"
echo "1. Set up environment variables in Render dashboard"
echo "2. Push code to GitHub:"
echo "   git add ."
echo "   git commit -m 'Deploy to Render'"
echo "   git push origin main"
echo "3. Connect GitHub repo to Render"
echo "4. Deploy! 🎉"

echo ""
echo "🔗 Useful Links:"
echo "- Render Dashboard: https://dashboard.render.com"
echo "- GitHub Repository: https://github.com/algsoch/chatbot_tds"
echo "- Deployment Guide: ./DEPLOYMENT.md"

echo ""
echo "✅ Deployment setup complete!"
