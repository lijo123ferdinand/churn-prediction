#!/usr/bin/env python3
"""
Create Django superuser if it doesn't exist.
This script checks if a superuser exists and creates one if needed.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'churn_prediction.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_superuser_if_needed():
    """Create superuser if none exists."""
    if User.objects.filter(is_superuser=True).exists():
        print("✅ Superuser already exists")
        return True
    
    print("📝 No superuser found. Creating one...")
    print("   You can customize credentials in this script or use environment variables")
    
    # Get credentials from environment or use defaults
    username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
    password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')
    
    try:
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        print(f"✅ Superuser created successfully!")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"\n⚠️  Please change the default password after first login!")
        return True
    except Exception as e:
        print(f"❌ Failed to create superuser: {e}")
        print("\n💡 You can create one manually with:")
        print("   python manage.py createsuperuser")
        return False

if __name__ == "__main__":
    create_superuser_if_needed()

