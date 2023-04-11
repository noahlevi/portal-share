import json
import copy
import logging

from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.core.serializers import serialize
from django.db import models
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.conf import settings
from rest_framework import serializers

from rest_framework.authtoken.models import Token

from .models import Order
from .serializers import (
    OrderSerializer,
    CreditsSerializer,
    UserSerializer,
    UserCompanySerializer,
)
from users.models import User, Credits, UserCompany
from django.shortcuts import render, get_object_or_404


log = logging.getLogger(__name__)


class UserCreditsView(LoginRequiredMixin, TemplateView):

    template_name = "portal/user/credits.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # user = User.objects.get(pk=self.request.user.id)
        total_available_credits = sum([credit.credits for credit in self.request.user.get_valid_credits_qs()])
        all_credits_qs = Credits.objects.filter(user=self.request.user)
        credits_serializer = CreditsSerializer(all_credits_qs, many=True).data
        credits = json.dumps(credits_serializer)

        context["credits"] = credits
        context["total_available_credits"] = total_available_credits

        return context


class UserOrdersView(LoginRequiredMixin, TemplateView):

    template_name = "portal/user/orders.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orders_qs = Order.objects.filter(user=self.request.user.id)
        orders_serializer = OrderSerializer(orders_qs, many=True).data
        orders = json.dumps(orders_serializer)
        context["orders"] = orders
        context["s3_base_url"] = settings.AWS_S3_BASE_URL
        return context


class UserApiKeyView(LoginRequiredMixin, TemplateView):

    template_name = "portal/user/api-key.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        api_token = None
        if Token.objects.filter(user=self.request.user.id).exists():
            api_token = Token.objects.get(user=self.request.user.id)
        context["api_token"] = api_token
        return context


class UserLogoutView(LoginRequiredMixin, TemplateView):

    template_name = "portal/user/logout.html"


# clients list
@method_decorator(staff_member_required, name="dispatch")
class AdminHomeView(LoginRequiredMixin, TemplateView):

    template_name = "portal/admin/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["users"] = json.dumps(UserSerializer(User.objects.all(), many=True).data)
        context["s3_base_url"] = settings.AWS_S3_BASE_URL
        return context

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        now = timezone.now()
        return JsonResponse(
            {
                "status": True,
                "id": data["user_id"],
                "credits": {
                    "total": User.objects.get(id=data["user_id"]).total_credits,
                    "active": CreditsSerializer(
                        Credits.objects.filter(user_id=data["user_id"], expiry_datetime__gt=now), many=True
                    ).data,
                    "expired": CreditsSerializer(
                        Credits.objects.filter(user_id=data["user_id"], expiry_datetime__lte=now), many=True
                    ).data,
                },
                "orders": OrderSerializer(Order.objects.filter(user_id=data["user_id"]), many=True).data,
            }
        )


# manage credits
@method_decorator(staff_member_required, name="dispatch")
class AdminDeleteCreditsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        credits_id = self.kwargs.get("credits_id")
        credits = get_object_or_404(Credits, pk=credits_id)
        credits.delete()
        return JsonResponse({"status": True})


@method_decorator(staff_member_required, name="dispatch")
class AdminAddOrUpdateCreditsView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        if data["type"] == "add":
            serializer = CreditsSerializer(data=data)
        elif data["type"] == "update":
            credits = Credits.objects.get(id=data["id"])
            serializer = CreditsSerializer(data=data, instance=credits)
        if serializer.is_valid():
            print("SAVING")
            x = serializer.save()
            print(x)
        else:
            print(serializer.errors)
        return JsonResponse({"status": True})


# manage orders
@method_decorator(staff_member_required, name="dispatch")
class AdminDeleteOrderView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user_id = self.kwargs.get("user_id")
        order_id = self.kwargs.get("order_id")
        order = get_object_or_404(Order, pk=order_id)
        order.delete()
        return JsonResponse(
            {
                "status": "deleted",
                "order_id": order_id,
                "message": f"Order {order_id} successfully deleted",
            },
            safe=False,
        )


@method_decorator(staff_member_required, name="dispatch")
class AdminAddOrUpdateOrderView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        user = User.objects.get(id=data["user"])
        if data["type"] == "add":
            serializer = OrderSerializer(data=data)
        elif data["type"] == "update":
            order = Order.objects.get(id=data["id"])
            serializer = OrderSerializer(data=data, instance=order)
        if serializer.is_valid():
            serializer.save()
            if data["deduct_credits"]:
                credits = int(data["total_charge"])
                log.info(f"Deducting {credits} from user | User: {user.email}")

                to_deduct = copy.copy(credits)
                # cycle through credit packages till all credits deducted
                for credits_obj in user.get_valid_credits_qs():
                    log.debug(
                        f"Looping through credits object for deduction | User: {user.email} | Credits ID: {credits_obj.id}"
                    )
                    if to_deduct <= credits_obj.credits:
                        log.debug(
                            f"Sufficient credits found in credit object. Deducting {to_deduct} from credit object {credits_obj.id} | User: {user.email} | Credits ID: {credits_obj.id}"
                        )
                        credits_obj.credits = models.F("credits") - to_deduct
                        credits_obj.save()
                        break
                    else:
                        current_credits = credits_obj.credits
                        to_deduct -= current_credits
                        log.debug(
                            f"Insufficient credits found in credit object. Deducting {current_credits} from credit object {credits_obj.id} | User: {user.email} | Credits ID: {credits_obj.id}"
                        )
                        credits_obj.credits = models.F("credits") - current_credits
                        credits_obj.save()
        else:
            return JsonResponse({"status": False, "errors": serializer.errors})
        return JsonResponse({"status": True})


class AdminCreateUserView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/admin/create-user.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        companies_qs = UserCompany.objects.all()
        companies_serializer = (
            UserCompanySerializer(companies_qs, many=True).data)
        companies = json.dumps(companies_serializer)

        context['companies'] = companies
        return context


class AdminUserCard(LoginRequiredMixin, TemplateView):

    template_name = 'admin/user_card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.kwargs.get("user_id")

        user_qs = User.objects.get(pk=user_id)
        user_serializer = (UserSerializer(user_qs).data)
        user = json.dumps(user_serializer)

        total_available_credits = sum(
            [credit.credits for credit in user_qs.get_valid_credits_qs()])

        context['user'] = user
        context['total_available_credits'] = total_available_credits
        return context


class AdminUpdateUser(LoginRequiredMixin, TemplateView):
    template_name = 'admin/update_user.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.kwargs.get("user_id")

        user_qs = User.objects.get(pk=user_id)
        user_serializer = (UserSerializer(user_qs).data)
        user = json.dumps(user_serializer)

        company_serializer = (
            UserCompanySerializer(user_qs.company).data)
        company = json.dumps(company_serializer)

        companies_qs = UserCompany.objects.all()
        companies_serializer = (
            UserCompanySerializer(companies_qs, many=True).data)
        companies = json.dumps(companies_serializer)

        context['date_joined'] = json.dumps(user_serializer['date_joined'])
        context['user'] = user
        context['companies'] = companies
        context['company'] = company
        return context


class UpdateUser(LoginRequiredMixin, View):
    def post(self, request, user_id, *args, **kwargs):
        user_data = json.loads(self.request.body)
        print(user_data)
        serializer = UserSerializer(data=user_data)
        user = User.objects.get(pk=user_id)
        print("Before is valid")
        if serializer.is_valid():
            print("User are valid. Attempting to save to db")
            serializer.update(instance=user,
                              validated_data=serializer.validated_data)
            return JsonResponse(
                {
                    "user_id": user_id,
                    "status": "updated",
                    "message": f"Successfully updated user {user_id}",
                }
            )
        else:
            print("error")
            print(serializer.errors)
            return JsonResponse(
                {"status": False, "errors": [
                    error for error in serializer.errors]}
            )


class CreateUser(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user_data = json.loads(self.request.body)
        print(user_data)
        serializer = UserSerializer(data=user_data)
        print("Before is valid")
        if serializer.is_valid():
            print("User are valid. Attempting to save to db")
            serializer.save()
            # serializer.update(instance=user,
            #                   validated_data=serializer.validated_data)
            return JsonResponse(
                {
                    "status": "added",
                    "message": f"Successfully added a new user",
                }
            )
        else:
            print("error")
            print(serializer.errors)
            return JsonResponse(
                {"status": False, "errors": [
                    error for error in serializer.errors]}
            )


class DeleteUser(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user_id = self.kwargs.get("user_id")
        user = get_object_or_404(
            User, pk=user_id)
        user.delete()
        return JsonResponse(
            {
                "status": "deleted",
                "order_id": user_id,
                "message": f"User {user_id} successfully deleted",
            },
            safe=False)


class AdminCreateCompany(LoginRequiredMixin, TemplateView):
    template_name = 'admin/create_company.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        companies_qs = UserCompany.objects.all()
        companies_serializer = (
            UserCompanySerializer(companies_qs, many=True).data)
        companies = json.dumps(companies_serializer)

        context['companies'] = companies

        return context

class CreateCompany(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        company_data = json.loads(self.request.body)
        print(company_data)
        serializer = UserCompanySerializer(data=company_data)
        print("Before is valid")
        if serializer.is_valid():
            print("Company are valid. Attempting to save to db")
            serializer.save()
            return JsonResponse(
                {
                    "status": "added",
                    "message": f"Successfully added a new company",
                }
            )
        else:
            print("error")
            print(serializer.errors)
            return JsonResponse(
                {"status": False, "errors": [
                    error for error in serializer.errors]}
            )


class AdminCompanyCard(LoginRequiredMixin, TemplateView):

    template_name = 'admin/company_card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company_id = self.kwargs.get("company_id")

        company_qs = UserCompany.objects.get(pk=company_id)
        company_serializer = (
            UserCompanySerializer(company_qs).data)
        company = json.dumps(company_serializer)

        total_users = len(User.objects.filter(company__id=company_id))
        print(total_users)

        context['company'] = company
        context['total_users'] = total_users
        return context


class AdminUpdateCompany(LoginRequiredMixin, TemplateView):
    template_name = 'admin/update_company.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        company_id = self.kwargs.get("company_id")

        companies_qs = UserCompany.objects.all()
        companies_serializer = (
            UserCompanySerializer(companies_qs, many=True).data)
        companies = json.dumps(companies_serializer)

        company_qs = UserCompany.objects.get(pk=company_id)
        company_serializer = (
            UserCompanySerializer(company_qs).data)
        company = json.dumps(company_serializer)

        context['companies'] = companies
        context['company'] = company
        return context


class UpdateCompany(LoginRequiredMixin, View):
    def post(self, request, company_id, * args, **kwargs):
        company_data = json.loads(self.request.body)

        company = UserCompany.objects.get(pk=company_id)
        serializer = UserCompanySerializer(data=company_data)
        print("Before is valid")
        if serializer.is_valid():
            print("Company are valid. Attempting to save to db")
            serializer.update(instance=company, validated_data=serializer.validated_data)
            return JsonResponse(
                {
                    "status": "updated",
                    "message": f"Successfully updated {company_id} company",
                }
            )
        else:
            print("error")
            print(serializer.errors)
            return JsonResponse(
                {"status": False, "errors": [
                    error for error in serializer.errors]}
            )


class DeleteCompany(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        company_id = self.kwargs.get("company_id")
        company = get_object_or_404(
            UserCompany, pk=company_id)
        company.delete()
        return JsonResponse(
            {
                "status": "deleted",
                "order_id": company_id,
                "message": f"Company {company_id} successfully deleted",
            }, safe=False)
