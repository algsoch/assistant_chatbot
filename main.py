#!/usr/bin/env python3
"""
TDS Assistant - Main Entry Point
AI-Powered Question Answering System for Data Science
"""
import uvicorn
from vicky_app import app
from src.core.config import settings

if __name__ == "__main__":
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🎯 TDS Assistant v{settings.APP_VERSION}                          ║
    ║   AI-Powered Question Answering System                    ║
    ║                                                           ║
    ╠═══════════════════════════════════════════════════════════╣
    ║                                                           ║
    ║   🌐 Server: http://{settings.HOST}:{settings.PORT}                       ║
    ║   📖 API Docs: http://localhost:{settings.PORT}/docs                ║
    ║   🔧 Debug Mode: {str(settings.DEBUG).lower()}                              ║
    ║                                                           ║
    ║   Press Ctrl+C to stop                                    ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "vicky_app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
