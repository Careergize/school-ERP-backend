"""Local development serving for the built React frontend."""
from pathlib import Path
from django.http import FileResponse, HttpResponse
from django.views.decorators.http import require_GET

UI_DIST=Path(__file__).resolve().parents[2]/'UI'/'dist'


@require_GET
def frontend_index(request):
    index=UI_DIST/'index.html'
    if not index.exists():
        return HttpResponse('Build the frontend first: cd UI and run npm run build, or use npm run dev on port 5173.',status=503,content_type='text/plain')
    response=FileResponse(index.open('rb'),content_type='text/html')
    response['Cache-Control']='no-cache'
    return response
