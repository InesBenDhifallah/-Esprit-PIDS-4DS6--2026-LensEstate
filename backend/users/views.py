from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from .models import Favorite, SavedSearch
from .serializers import (
    UserSerializer, RegisterSerializer,
    FavoriteSerializer, SavedSearchSerializer
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # validate password strength
        try:
            validate_password(request.data.get('password'))
        except ValidationError as e:
            return Response({'password': list(e.messages)}, status=400)

        user = serializer.save()

        # create email address record
        email_address = EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=False
        )

        # send verification email
        try:
            confirmation = EmailConfirmationHMAC(email_address)
            confirmation.send(request, signup=True)
        except Exception as e:
            # if email fails, still create the account
            # just log the error — don't block registration
            print(f"Email sending failed: {e}")

        return Response(
            {'message': 'Account created. Please check your email to verify your account.'},
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Username and password required'}, status=400)

        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response({'error': 'Invalid credentials'}, status=401)

        if not user.is_active:
            return Response({'error': 'Account is disabled'}, status=401)

        # check email verification
        if not EmailAddress.objects.filter(user=user, verified=True).exists():
            return Response(
                {'error': 'Please verify your email before logging in'},
                status=401
            )

        # generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # create server-side session
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # blacklist the refresh token
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass

        # destroy server-side session
        logout(request)

        return Response({'message': 'Logged out successfully'})


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email required'}, status=400)

        try:
            from allauth.account.forms import ResetPasswordForm
            form = ResetPasswordForm(data={'email': email})
            if form.is_valid():
                form.save(request)
        except Exception as e:
            print(f"Password reset error: {e}")

        # always return success — never reveal if email exists
        return Response(
            {'message': 'If this email exists, a reset link has been sent.'}
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password')

        if not all([uid, token, password]):
            return Response({'error': 'uid, token and password are required'}, status=400)

        try:
            from allauth.account.forms import UserTokenForm
            # validate uid + token
            token_form = UserTokenForm(data={'uidb36': uid, 'key': token})
            if not token_form.is_valid():
                return Response({'error': 'Invalid or expired reset link'}, status=400)

            user = token_form.reset_user

            # validate password strength
            try:
                validate_password(password, user=user)
            except ValidationError as e:
                return Response({'password': list(e.messages)}, status=400)

            # set the new password
            from allauth.account.internal.flows.password_reset import reset_password
            reset_password(user, password)
            return Response({'message': 'Password reset successful'})
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class FavoriteListView(generics.ListCreateAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FavoriteDeleteView(generics.DestroyAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)


class SavedSearchListView(generics.ListCreateAPIView):
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('access_token')
        if not token:
            return Response({'error': 'access_token required'}, status=400)

        try:
            # verify the token with Google
            import requests as http_requests
            google_response = http_requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {token}'}
            )

            if google_response.status_code != 200:
                return Response({'error': 'Invalid Google token'}, status=401)

            google_data = google_response.json()
            email = google_data.get('email')
            name = google_data.get('name', '')
            google_id = google_data.get('sub')

            if not email:
                return Response({'error': 'Could not get email from Google'}, status=400)

            # get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': name.split(' ')[0] if name else '',
                    'last_name': name.split(' ')[-1] if name else '',
                }
            )

            # mark email as verified since Google already verified it
            EmailAddress.objects.get_or_create(
                user=user,
                email=email,
                defaults={'primary': True, 'verified': True}
            )
            # make sure it's verified even if record already existed
            EmailAddress.objects.filter(user=user, email=email).update(verified=True)

            # generate JWT tokens
            refresh = RefreshToken.for_user(user)

            # create session
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
                'created': created  # true if new user, false if existing
            })

        except Exception as e:
            return Response({'error': str(e)}, status=500)