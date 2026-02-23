from app.core.config import settings
import os

print(f"Current Directory: {os.getcwd()}")
print(f"Env File Expected At: {settings.Config.env_file}")
print(f"Env File Exists: {os.path.exists(settings.Config.env_file)}")

print("-" * 20)
print(f"ENVIRONMENT:      {settings.ENVIRONMENT}")
print(f"USE_REAL_MAIL:    {settings.USE_REAL_MAIL}")
print(f"MAIL_SERVER:      {settings.MAIL_SERVER}")
print(f"MAIL_PORT:        {settings.MAIL_PORT}")
print(f"MAIL_USERNAME:    {settings.MAIL_USERNAME}")
print(f"MAIL_FROM:        {settings.MAIL_FROM}")
print(f"MAIL_STARTTLS:    {settings.MAIL_STARTTLS}")
print(f"MAIL_SSL_TLS:     {settings.MAIL_SSL_TLS}")
print("-" * 20)
