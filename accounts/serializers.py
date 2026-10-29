from django.apps import apps
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=apps.get_model('students.Student').objects.all(), required=False, allow_null=True)
    staff_id = serializers.PrimaryKeyRelatedField(source='staff', queryset=apps.get_model('hr.Staff').objects.all(), required=False, allow_null=True)
    parent_id = serializers.PrimaryKeyRelatedField(source='parent', queryset=apps.get_model('students.Guardian').objects.all(), required=False, allow_null=True)
    password = serializers.CharField(write_only=True, min_length=12, trim_whitespace=False)

    class Meta:
        model = User
        fields = ['id','name','email','role','student_id','staff_id','parent_id','password']
        read_only_fields = ['id']

    def to_internal_value(self,data):
        data=data.copy()
        for key in ['student_id','staff_id','parent_id']:
            if data.get(key)=='': data[key]=None
        return super().to_internal_value(data)

    def validate_email(self,value): return value.lower()

    def validate(self,attrs):
        candidate=User(**{key:value for key,value in attrs.items() if key!='password'})
        try:
            candidate.clean()
            validate_password(attrs['password'], candidate)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc,'message_dict') else exc.messages)
        return attrs

    def create(self,validated_data):
        return User.objects.create_user(**validated_data)
