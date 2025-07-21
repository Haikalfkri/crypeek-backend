from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import *

import re

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = User.objects.filter(email=attrs['email']).first()
        if not user:
            raise serializers.ValidationError("User not found.")
        if not user.check_password(attrs['password']):
            raise serializers.ValidationError("Invalid password.")
        return attrs
    


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name']

class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role.name')
    subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'subscribed', 'date_joined']

    def get_subscribed(self, obj):
        return obj.is_subscribed

    def update(self, instance, validated_data):
        role_name = validated_data.pop('role', {}).get('name')
        if role_name:
            role = Role.objects.filter(name=role_name).first()
            if role:
                instance.role = role
        return super().update(instance, validated_data)


class UserFeedbackSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model: UserFeedback
        fields = ['id', 'username', 'email', 'feedback', 'created_at']


class CryptoSymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoSymbols
        fields = ['name']


class UserFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFeedback
        fields = '__all__'


class CryptoNewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoNews
        fields = [
            'title', 'description', 'summary', 'sentiment', 'image', 'link', 'published_at'
        ]


class CryptoInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoInsight
        fields = ['title', 'link', 'date', 'source', 'image', 'category']


class BasePredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BTCUSDT_Prediction  # default, nanti akan diganti dinamis di view
        fields = '__all__'

        def to_representation(self, instance):
            data = super().to_representation(instance)
        
            if 'price_analysis' in data and 'daily_explanations' in data['price_analysis']:
                explanations = data['price_analysis']['daily_explanations']
                data['price_analysis']['daily_explanations'] = [
                    re.sub(r'^\d+\.\s*', '', exp) for exp in explanations
                ]
            
            return data
        



