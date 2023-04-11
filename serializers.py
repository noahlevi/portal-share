from rest_framework import serializers
from .models import Order
from users.models import Credits, User, UserCompany


class CompanyField(serializers.Field):
    def to_representation(self, value):
        return UserCompanySerializer(value).data

    def to_internal_value(self, data):
        try:
            return UserCompany.objects.filter(id=data["id"]).first()
        except (AttributeError, KeyError):
            pass


class UserSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    credits = serializers.ReadOnlyField(source="total_credits")

    first_name = serializers.CharField(allow_blank=False, allow_null=False, required=True)
    last_name = serializers.CharField(allow_blank=False, allow_null=False, required=True)
    email = serializers.CharField(allow_blank=False, allow_null=False, required=True)
    company = CompanyField()
    date_joined = serializers.DateTimeField()

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "company", "date_joined", "credits"]

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.email = validated_data.get("email", instance.email)
        instance.company = validated_data.get("company", instance.company)
        instance.date_joined = validated_data.get("date_joined", instance.date_joined)
        instance.save()
        return instance


class OrderSerializer(serializers.ModelSerializer):

    s3_link = serializers.ReadOnlyField(source="tas.s3_link")

    class Meta:
        model = Order
        fields = ["id", "user", "name", "created", "currency", "total_charge", "service_charge", "tas", "s3_link"]

    # def update(self, instance, validated_data):
    #     instance.name = validated_data.get("name", instance.name)
    #     instance.payment_type = validated_data.get("payment_type", instance.payment_type)
    #     instance.created = validated_data.get("created", instance.created)
    #     instance.consumed_amount = validated_data.get("consumed_amount", instance.consumed_amount)
    #     instance.service_charge = validated_data.get("service_charge", instance.service_charge)
    #     instance.url = validated_data.get("url", instance.url)
    #     instance.save()
    #     return instance


class CreditsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credits
        fields = ["id", "user", "start_datetime", "credits", "expiry_datetime"]


class UserCompanySerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField(allow_blank=False, allow_null=False, required=True)

    class Meta:
        model = UserCompany
        fields = ["id", "name"]

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.save()
        return instance

