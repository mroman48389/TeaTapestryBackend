# How to Run Tea Tapestry Backend. 

> This doc explains how to run Tea Tapestry Backend in each mode. Assumes .env file is appropriately set. 
> See env.example for what is expected. Environment variables are declared in src/core/config/base_config.
> Other config files in src/core/config control behavior in different modes by inheriting from base config
> and overriding certain environment variables. There is local_config.py for local /
> development mode, preview_config.py for preview mode, production_config.py for production mode, and
> staging_config.py for staging mode. CORS can be changed in src/core/cors.py.

## 1. Local/Development Mode

> Run scripts\PowerShell\run.ps1 from the project. If you have not already activated the venv, the script
> will do it for you and then run the server.

## 2. Production Mode (Deployment)

> Make sure there are no linting errors, all tests pass, and the security audit passes by invoking the 
> fix.ps1, coverage.ps1, test.ps1, detect_n_plus_one_patterns.ps1, and security_audit.ps1 scripts. 
> Commit and push. Then open a Windows PowerShell prompt and do fly deploy. 