import io
import sys
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from rest_framework.permissions import AllowAny

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

housegan_path = os.path.join(BASE_DIR, "housegan")
if housegan_path not in sys.path:
    sys.path.append(housegan_path)

from housegan.inference_helper import generate_plan_from_graph

class GeneratePlanView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            rooms = data.get('rooms', [])
            edges = data.get('edges', [])
            
            checkpoint_path = os.path.join(BASE_DIR, 'housegan', 'checkpoints', 'exp_demo_D_500000.pth')
            img = generate_plan_from_graph(rooms, edges, checkpoint_path=checkpoint_path)
            
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            
            return HttpResponse(buf.getvalue(), content_type="image/png")
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
