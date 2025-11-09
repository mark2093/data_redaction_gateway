"""
New modular main entry point for PII/PCI Data Redaction Gateway.
"""

if __name__ == "__main__":
    import uvicorn
    from src.api.main import app
    from src.config import get_config
    
    # Load configuration
    config = get_config()
    
    # Run the application
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        workers=config.server.workers,
        reload=config.server.reload
    )