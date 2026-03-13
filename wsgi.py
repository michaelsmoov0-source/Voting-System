import os
import sys
from django.core.wsgi import get_wsgi_application

# Add the backend directory to Python path for monorepo structure
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
