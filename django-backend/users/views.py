import random
import string
import smtplib
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
# from fpdf import FPDF
from email.message import EmailMessage
from django.conf import settings
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import CustomUser,Role,DisposableDomains
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.utils import timezone
import uuid
import socket
import platform
import psutil
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from django.forms.models import model_to_dict

class UserAPIView(viewsets.ViewSet):
    """
    API endpoints for managing CustomUser.
    """

    @swagger_auto_schema(
        operation_summary="Get all users (with filters)",
        operation_description="Retrieve a list of users with optional filters: email, phone_number, role, is_authorized, is_verified.",
        manual_parameters=[
            openapi.Parameter('email', openapi.IN_QUERY, description="Filter by email", type=openapi.TYPE_STRING),
            openapi.Parameter('phone_number', openapi.IN_QUERY, description="Filter by phone number", type=openapi.TYPE_STRING),
            openapi.Parameter('role', openapi.IN_QUERY, description="Filter by role id", type=openapi.TYPE_INTEGER),
            openapi.Parameter('is_authorized', openapi.IN_QUERY, description="Filter by active status (true/false)", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_verified', openapi.IN_QUERY, description="Filter by verified status (true/false)", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('country_code', openapi.IN_QUERY, description="Filter by country code", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response("List of filtered users", openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "results": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
                    "status": openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            ))
        },
    )
    def list(self, request):
        users = CustomUser.objects.all()

        email = request.query_params.get('email')
        phone_number = request.query_params.get('phone_number')
        role = request.query_params.get('role')
        is_authorized = request.query_params.get('is_authorized')
        is_verified = request.query_params.get('is_verified')
        country_code = request.query_params.get('country_code')
        if email:
            users = users.filter(email__icontains=email)
        if phone_number:
            users = users.filter(phone_number__icontains=phone_number)
        if role:
            users = users.filter(role_id=role)
        if country_code:
            users = users.filter(country_code=country_code)
        if is_authorized is not None:
            users = users.filter(is_authorized=is_authorized.lower() == 'true')
        if is_verified is not None:
            users = users.filter(is_verified=is_verified.lower() == 'true')

        # Order by latest ID
        users = users.order_by('-id')

        # Convert to list and exclude 'password'
        user_data = []
        for user in users:
            user_dict = model_to_dict(user)
            user_dict.pop('password', None)
            user_dict['role_name'] = user.role.name if user.role else None
            user_data.append(user_dict)


        return Response({"results": user_data, "status": status.HTTP_200_OK})


    @swagger_auto_schema(
        operation_summary="Get a user",
        operation_description="Retrieve a specific user by ID.",
        responses={
            200: openapi.Response("User data", openapi.Schema(type=openapi.TYPE_OBJECT)),
            404: "User not found"
        },
        manual_parameters=[
            openapi.Parameter('id', openapi.IN_PATH, description="User ID", type=openapi.TYPE_INTEGER),
        ],
    )
    def retrieve(self, request, pk=None):
        user = CustomUser.objects.filter(pk=pk).first()

        if not user:
            return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        user_data = model_to_dict(user)
        user_data.pop('password', None)
        user_data['role_name'] = user.role.name if user.role else None


        return Response({"results": user_data}, status=status.HTTP_200_OK)

    # @swagger_auto_schema(
    #     operation_summary="Create a new user",
    #     operation_description="Registers a new user with the provided details.",
    #     request_body=openapi.Schema(
    #         type=openapi.TYPE_OBJECT,
    #         properties={
    #             "first_name": openapi.Schema(type=openapi.TYPE_STRING),
    #             "last_name": openapi.Schema(type=openapi.TYPE_STRING),
    #             "email": openapi.Schema(type=openapi.TYPE_STRING),
    #             "country_code": openapi.Schema(type=openapi.TYPE_STRING),
    #             "phone_number": openapi.Schema(type=openapi.TYPE_INTEGER),
    #             "password": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
    #             "mac_address": openapi.Schema(type=openapi.TYPE_STRING),
    #             "role_id": openapi.Schema(type=openapi.TYPE_INTEGER),
    #             "is_authorized": openapi.Schema(type=openapi.TYPE_BOOLEAN),
    #             "started_on": openapi.Schema(type=openapi.TYPE_STRING, format="date")
    #         }
    #     ),
    #     responses={201: "User created", 400: "Invalid data"},
    # )
    # def create(self, request):
    #     data = request.data
    #     email = data.get("email")
    #     phone_number = str(data.get("phone_number"))
    #     mac_address = data.get("mac_address")

    #     # ✅ Check if email is disposable

    #     domain = email.split("@")[-1].lower()
    #     if DisposableDomains.objects.filter(domain_name__iexact=domain).exists():
    #         return Response({"message": "Disposable emails are not allowed.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
    #     if CustomUser.objects.filter(email=email).exists():
    #         return Response({"message": "A user with this email already exists.","status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
    
        
    #     # Check if phone number already exists
    #     if CustomUser.objects.filter(phone_number=phone_number).exists():
    #         return Response({"message": "A user with this phone number already exists.","status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

    #     # if CustomUser.objects.filter(mac_address=mac_address).exists():
    #     #     return Response({"message":"A user is already existing with this device please contact admin","status":status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        
    #     # ✅ Generate secret key
    #     secret_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

    #     # ✅ Generate password if not provided
    #     password = data.get("password") or ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=10))

    #     # ✅ Prepare PDF content
    #     pdf_content = f"Your secret key: {secret_key}"
    #     if request.data.get("password") is None:
    #         pdf_content += f"\nYour generated password: {password}"

    #     # ✅ Generate & Encrypt PDF
    #     pdf = FPDF()
    #     pdf.add_page()
    #     pdf.set_font("Arial", size=12)
    #     pdf.multi_cell(0, 10, pdf_content)

    #     pdf_output = BytesIO()
    #     pdf.output(pdf_output, 'F')
    #     pdf_output.seek(0)

    #     pdf_reader = PdfReader(pdf_output)
    #     pdf_writer = PdfWriter()
    #     pdf_writer.add_page(pdf_reader.pages[0])
    #     pdf_writer.encrypt(phone_number)

    #     encrypted_pdf = BytesIO()
    #     pdf_writer.write(encrypted_pdf)
    #     encrypted_pdf.seek(0)

    #     # ✅ Send Email with Encrypted PDF
    #     msg = EmailMessage()
    #     msg['Subject'] = "Your Account Details"
    #     msg['From'] = settings.EMAIL_HOST_USER
    #     msg['To'] = email
    #     msg.set_content("Please find your login credentials in the attached encrypted PDF.\nThe password to open the PDF is your phone number.")

    #     msg.add_attachment(encrypted_pdf.read(), maintype="application", subtype="pdf", filename="User_Credentials.pdf")

    #     try:
    #         with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
    #             server.starttls()
    #             server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    #             server.send_message(msg)
    #     except Exception as e:
    #         return Response({"message": f"Email sending failed: {e}","status":status.HTTP_500_INTERNAL_SERVER_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #     # ✅ Create User in Database
    #     user = CustomUser.objects.create(
    #         username=data["email"],
    #         first_name=data["first_name"],
    #         last_name=data["last_name"],
    #         email=email,
    #         country_code=data['country_code'],
    #         phone_number=data['phone_number'],
    #         password=make_password(password),
    #         secret_key=secret_key,
    #         mac_address=mac_address,
    #         role_id=data.get("role_id"),
    #         is_authorized=data.get("is_authorized", True),
    #         started_on=data.get("started_on")
    #     )

    #     # ✅ Get role name and form success message
    #     try:
    #         role = Role.objects.get(id=data.get("role_id"))
    #         role_name = role.name
    #         message = f"{role_name} created successfully"
    #     except Role.DoesNotExist:
    #         message = "User created successfully"

    #     return Response({
    #         "message": message,
    #         "user_id": user.id,
    #         "status": status.HTTP_201_CREATED
    #     }, status=status.HTTP_201_CREATED)
        
        
    @swagger_auto_schema(
        operation_summary="Update a user",
        operation_description="Update an existing user's details.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING),
                "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "country_code": openapi.Schema(type=openapi.TYPE_STRING),
                "phone_number": openapi.Schema(type=openapi.TYPE_INTEGER),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
                "secret_key": openapi.Schema(type=openapi.TYPE_STRING),
                "serial_number": openapi.Schema(type=openapi.TYPE_STRING),
                "role_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "is_authorized": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                "started_on": openapi.Schema(type=openapi.TYPE_STRING, format="date")
            }
        ),
        responses={200: "User updated", 404: "User not found"},
    )
    def update(self, request, pk=None):
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"message": "User not found","status":status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        for key, value in request.data.items():
            setattr(user, key, value)
        user.save()
        return Response({"message": "User updated successfully"})

    @swagger_auto_schema(
        operation_summary="Delete a user",
        operation_description="Delete a user by ID.",
        responses={204: "User deleted", 404: "User not found"},
    )
    def destroy(self, request, pk=None):
        try:
            user = CustomUser.objects.get(pk=pk)
            user.delete()
            return Response({"message": "User deleted successfully","status":204}, status=status.HTTP_204_NO_CONTENT)
        except CustomUser.DoesNotExist:
            return Response({"message": "User not found","status":status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)


class LoginAPIView(viewsets.ViewSet):
    @swagger_auto_schema(
        operation_summary="Login",
        operation_description="Logs in a user using email or phone number and password, and returns JWT tokens.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="User's email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="User's password"),
            },
            required=["email", "password"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "access_token": openapi.Schema(type=openapi.TYPE_STRING),
                    "refresh_token": openapi.Schema(type=openapi.TYPE_STRING),
                    "role_name": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
            400: "Invalid credentials",
            404: "User not found",
            429: "Too many failed attempts. Try again later.",
        },
    )
    def create(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"message": "Email and password are required","status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        user = CustomUser.objects.filter(email=email).first()
        
        if not user:
            return Response({"message": "Invalid email or password","status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_authorized is False:
            return Response({"message": "User is not authorized to login please contact admin","status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Check if user is blocked due to too many failed attempts
        if user.failed_login_attempts >= 5:
            block_period = timedelta(minutes=5)
            block_time = user.last_failed_login + block_period
            if timezone.now() < block_time:
                wait_time = int((block_time - timezone.now()).total_seconds() // 60)
                return Response(
                    {"message": f"Too many failed attempts. Try again after {wait_time + 1} minutes.","status": status.HTTP_429_TOO_MANY_REQUESTS},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        # ✅ Check password
        if check_password(password, user.password):
            user.failed_login_attempts = 0
            
            user.save()

            # ✅ Generate JWT Tokens
            refresh = RefreshToken.for_user(user)

            response_data = {
                "message": "Login successful",
                "role_id":user.role_id if user.role else None,
                "role_name": user.role.name if user.role else None,
                "user_id":user.id,
                "first_name":user.first_name,
                "last_name":user.last_name,
                "email":user.email,
                "user_created_date":user.started_on,
                "secret_key_verified":user.secret_key_verified,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            }

            # ✅ If user role is "user", generate and email a new secret key
            # if user.role.name.lower() == "user":
            #     secret_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
            #     user.secret_key = secret_key
            #     user.save()

            #     # ✅ Generate a unique identifier for the email subject
            #     unique_id = uuid.uuid4().hex[:8]

            #     # ✅ Create PDF content
            #     pdf_content = f"Your new secret key: {secret_key}"

            #     pdf = FPDF()
            #     pdf.add_page()
            #     pdf.set_font("Arial", size=12)
            #     pdf.multi_cell(0, 10, pdf_content)

            #     pdf_output = BytesIO()
            #     pdf.output(pdf_output, 'F')
            #     pdf_output.seek(0)

            #     # ✅ Encrypt PDF (Password = User's phone number)
            #     pdf_reader = PdfReader(pdf_output)
            #     pdf_writer = PdfWriter()
            #     pdf_writer.add_page(pdf_reader.pages[0])
            #     pdf_writer.encrypt(str(user.phone_number))  # Phone number as password

            #     encrypted_pdf = BytesIO()
            #     pdf_writer.write(encrypted_pdf)
            #     encrypted_pdf.seek(0)

            #     # ✅ Send Email with Encrypted PDF
            #     msg = EmailMessage()
            #     msg['Subject'] = f"Your Secret Key [{unique_id}]"  # Unique email subject
            #     msg['From'] = settings.EMAIL_HOST_USER
            #     msg['To'] = email
            #     msg.set_content(
            #         f"Dear {user.first_name},\n\nYour new secret key is in the attached encrypted PDF.\n"
            #         f"The password to open the PDF is your phone number."
            #     )

            #     msg.add_attachment(encrypted_pdf.read(), maintype="application", subtype="pdf", filename="Secret_Key.pdf")

            #     try:
            #         with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            #             server.starttls()
            #             server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            #             server.send_message(msg)
            #     except Exception as e:
            #         return Response({"message": f"Email sending failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            #     response_data["secret_key"] = "A new secret key has been sent to your email."

            return Response(response_data, status=status.HTTP_200_OK)

        else:
            # ✅ Increment failed login attempts
            user.failed_login_attempts += 1
            user.last_failed_login = timezone.now()
            user.save()
            return Response({"message": "Invalid email or password","status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        

class SecretKeyValidationAPI(viewsets.ViewSet):
    
    @swagger_auto_schema(
        operation_description="Validate secret key for a given user ID",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['user_id', 'secret_key'],
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
                'secret_key': openapi.Schema(type=openapi.TYPE_STRING, description='Secret Key'),
            },
        ),
        responses={
            200: openapi.Response(
                description="Validation result",
                examples={
                    "application/json": {
                        "valid": True,
                        "message": "Secret key is valid"
                    }
                }
            ),
            404: "User not found",
            400: "Invalid request"
        }
    )
    def create(self, request):
        user_id = request.data.get("user_id")
        secret_key = request.data.get("secret_key")

        if not user_id or not secret_key:
            return Response(
                {"valid": False, "message": "user_id and secret_key are required","status":status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"valid": False, "message": "User not found","status":status.HTTP_404_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.secret_key == secret_key:
            if not user.is_verified:
                user.is_verified = True  #### making is verified flag true ####
            if not user.secret_key_verified:
                user.secret_key_verified = True ### making secret_key_verified flag true #####
            user.save()
                
            return Response(
                {"valid": True, "message": "Secret key is valid","status":status.HTTP_200_OK},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"valid": False, "message": "Invalid secret key","status":status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST
            )

class ResetPasswordAPIView(viewsets.ViewSet):

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='User email')
            },
            required=['email']
        ),
        operation_summary="Send Password Reset Link",
        responses={200: openapi.Response(description="Password reset link sent successfully")}
    )
    def create(self, request):
        email = request.data.get('email')

        if not email:
            return Response({'message': 'Email is required',"status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'message': 'User not found',"status":status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        # Generate unique token and set expiration time
        token = str(uuid.uuid4())
        expiration_time = timezone.now() + timedelta(minutes=10)


        user.link_expire_token = token
        user.last_failed_login = expiration_time  # Reuse this field for expiry
        user.save(update_fields=['link_expire_token', 'last_failed_login'])

        domain = request.get_host()  # e.g., "hul.indusvision.ai"
        scheme = 'https' if request.is_secure() else 'http'
        reset_link = f'{scheme}://{domain}/reset-password/{user.id}/?token={token}'

        context = {
            'first_name': user.first_name,
            'login_url': reset_link,
        }

        html_content = render_to_string('reset-password.html', context)

        email_message = EmailMultiAlternatives(
            subject='Password Reset Request',
            body='Please use the HTML version.',
            from_email=settings.EMAIL_HOST_USER,
            to=[email]
        )
        email_message.attach_alternative(html_content, 'text/html')
        email_message.send()

        return Response({'message': 'Password reset link sent successfully',"status":status.HTTP_200_OK}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'new_password': openapi.Schema(type=openapi.TYPE_STRING),
                'confirm_password': openapi.Schema(type=openapi.TYPE_STRING),
                'token': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['new_password', 'confirm_password', 'token']
        ),
        operation_summary="Update User Password",
        responses={200: openapi.Response(description="Password updated successfully")}
    )
    def update(self, request, pk):
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        token = request.data.get('token')

        if not all([new_password, confirm_password, token]):
            return Response({'message': 'All fields are required',"status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({'message': 'Passwords do not match',"status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(id=pk, link_expire_token=token)
        except CustomUser.DoesNotExist:
            return Response({'message': 'Invalid user or token',"status":status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        if not user.last_failed_login or user.last_failed_login < timezone.now():
            return Response({'message': 'Token has expired',"status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.link_expire_token = None
        user.last_failed_login = None
        user.save()

        return Response({'message': 'Password updated successfully',"status":status.HTTP_200_OK}, status=status.HTTP_200_OK)
    

class ValidateResetLink(viewsets.ViewSet):

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'token': openapi.Schema(type=openapi.TYPE_STRING, description="Reset token")
            },
            required=['token']
        ),
        operation_summary="Validate Password Reset Token",
        responses={
            200: openapi.Response(description="Token is valid"),
            400: openapi.Response(description="Invalid request"),
            401: openapi.Response(description="Token expired or invalid")
        }
    )
    def create(self, request):
        token = request.data.get('token')

        if not token:
            return Response({'message': 'Token is required',"status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(link_expire_token=token)
        except CustomUser.DoesNotExist:
            return Response({'message': 'Invalid token',"status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the token is expired
        if not user.last_failed_login or user.last_failed_login < timezone.now():
            return Response({
                'message': 'Link has expired, please request a new one to reset your password.',
                'expired': True,
                "status":status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Token is valid',"status":status.HTTP_200_OK}, status=status.HTTP_200_OK)
    


import socket
import platform
import psutil
from rest_framework import viewsets
from rest_framework.response import Response

class SystemInfoViewSet(viewsets.ViewSet):
    def list(self, request):
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        # Get the active interface's MAC address
        mac = None
        interfaces = psutil.net_if_addrs()
        for iface_name, iface_addresses in interfaces.items():
            for addr in iface_addresses:
                if addr.family == psutil.AF_LINK and not addr.address.startswith("00:00"):
                    mac = addr.address
                    break
            if mac:
                break

        # Fallback if MAC still not found
        if not mac:
            mac = "Unavailable"

        # Gather system info
        system = platform.system()
        release = platform.release()
        version = platform.version()
        processor = platform.processor()
        architecture = platform.machine()

        # Network interface IPv4s
        interface_data = {
            name: [str(addr.address) for addr in addrs if addr.family == socket.AF_INET]
            for name, addrs in interfaces.items()
        }

        return Response({
            "mac_address": mac,
            "local_ip": local_ip,
            "hostname": hostname,
            "system": system,
            "release": release,
            "version": version,
            "architecture": architecture,
            "processor": processor,
            "network_interfaces": interface_data
        })

class MacAddressValidationViewSet(viewsets.ViewSet):
    """
    Validates if the provided MAC address matches the user's stored MAC address.
    """

    @swagger_auto_schema(
        operation_summary="Validate User Serial Number",
        operation_description="Takes `user_id` and `serial_number` as query params and checks if the serial number is valid for the user.",
        manual_parameters=[
            openapi.Parameter('user_id', openapi.IN_QUERY, description="User ID", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('serial_number', openapi.IN_QUERY, description="MAC address to validate", type=openapi.TYPE_STRING, required=True),
        ],
        responses={
            200: openapi.Response(description="MAC address is valid."),
            400: openapi.Response(description="MAC address is invalid."),
            404: openapi.Response(description="User not found."),
        }
    )
    def list(self, request):
        user_id = request.query_params.get("user_id")
        serial_number = request.query_params.get("serial_number")

        if not user_id or not serial_number:
            return Response({
                "message": "Both User Id and Serial Number are required.","status": status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                "message": "User not found.","status": status.HTTP_404_NOT_FOUND
            }, status=status.HTTP_404_NOT_FOUND)

        if user.serial_number == serial_number:
            return Response({
                "message": "Serial number is valid.","status": status.HTTP_200_OK
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "message":"Serial number is invalid.","status": "N5000"
            })
            
class RoleViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_description="Get list of active roles",
        responses={
            200: openapi.Response(
                description="List of roles",
                examples={
                    "application/json": [
                        {"id": 1, "name": "Admin", "is_active": True},
                        {"id": 2, "name": "Teacher", "is_active": True},
                    ]
                },
            )
        }
    )
    def list(self, request):
        roles = Role.objects.filter(is_active=True).values("id", "name", "is_active")
        return Response({"results":list(roles)}, status=status.HTTP_200_OK)
    
from django.http import JsonResponse as JSONResponse

def index(request):
    """
    Serve the React frontend.
    """
    return JSONResponse({"message": "Welcome to the Nexify API!"}, status=200)