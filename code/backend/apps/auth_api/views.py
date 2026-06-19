"""
AlphaFX Auth API
Thin wrapper around Django auth + SimpleJWT that returns the
{ token, user } envelope the frontend AuthContext expects.

Endpoints (all under /api/v1/auth/):
  POST   login/            { username, password } -> { token, user }
  POST   register/         { username, email, password, ... } -> { token, user }
  GET    me/               -> user object  (requires Bearer token)
  PATCH  profile/          { first_name, last_name, email } -> user object
  POST   change-password/  { old_password, new_password } -> 200
"""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_dict(user: User) -> dict:
    return {
        "id": str(user.pk),
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "date_joined": user.date_joined.isoformat(),
        "plan": "free",  # placeholder; extend when a subscription model is added
    }


def _token_for(user: User) -> str:
    """Return a short-lived access token string."""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")


class ProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class LoginView(APIView):
    """POST /api/v1/auth/login/ -- authenticate and return { token, user }."""

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=ser.validated_data["username"],
            password=ser.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response({"token": _token_for(user), "user": _user_dict(user)})


class RegisterView(APIView):
    """POST /api/v1/auth/register/ -- create account and return { token, user }."""

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        if User.objects.filter(username=d["username"]).exists():
            return Response(
                {"detail": "Username already taken."},
                status=status.HTTP_409_CONFLICT,
            )

        user = User.objects.create_user(
            username=d["username"],
            email=d["email"],
            password=d["password"],
            first_name=d.get("first_name", ""),
            last_name=d.get("last_name", ""),
        )

        return Response(
            {"token": _token_for(user), "user": _user_dict(user)},
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """GET /api/v1/auth/me/ -- return current user. Requires Bearer token."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_dict(request.user))


class ProfileView(APIView):
    """PATCH /api/v1/auth/profile/ -- update name / email. Requires Bearer token."""

    permission_classes = [IsAuthenticated]

    def patch(self, request):
        ser = ProfileUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        user = request.user
        for field in ("first_name", "last_name", "email"):
            if field in d:
                setattr(user, field, d[field])
        user.save()

        return Response(_user_dict(user))


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/ -- change password. Requires Bearer token."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        user = request.user
        if not user.check_password(d["old_password"]):
            return Response(
                {"detail": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(d["new_password"])
        user.save()

        return Response({"detail": "Password updated."})
